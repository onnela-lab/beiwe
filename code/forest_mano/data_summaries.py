"""User-friendly functions for either using mano to download data or download
 Beiwe summary statistics from the Tableau endpoint"""

from datetime import datetime
import logging
import requests
import os
import sys
import cryptease
import mano
import pandas as pd
import numpy as np
import importlib
import matplotlib.pyplot as plt
from mano.sync import BACKFILL_START_DATE


logger = logging.getLogger(__name__)

DATA_STREAMS_WITH_FOREST_TREES = [
    "gps", "accelerometer", "calls", "texts", "survey_answers",
    "survey_timings", "audio_recordings"
]

KEYRING_FIELDS = ["URL", "USERNAME", "PASSWORD", "ACCESS_KEY", "SECRET_KEY",
                  "TABLEAU_ACCESS_KEY", "TABLEAU_SECRET_KEY"]

KEYRING_DESCRIPTIONS = {
    "URL": "URL: The website you log in to see Beiwe study and participant"
           " information (ex. https://studies.beiwe.org)",
    "USERNAME": "USERNAME: The username you use when signing in to see Beiwe "
                "study and participant information",

    "PASSWORD": "PASSWORD: The password you use when signing in to see Beiwe "
                " study and participant information",
    "ACCESS_KEY": "ACCESS_KEY: The access key generated by clicking "
                  "'Manage Credentials' then selecting "
                  "'Generate Data-Download API Access "
                  "Credentials' under 'Generate New "
                  "Data-Download API Access Credentials",
    "SECRET_KEY": "SECRET_KEY: The secret key generated by clicking "
                  "'Manage Credentials' then selecting "
                  "'Generate Data-Download API Access "
                  "Credentials' under 'Generate New "
                  "Data-Download API Access Credentials",
    "TABLEAU_ACCESS_KEY": "TABLEAU_ACCESS_KEY: The access key generated by "
                          "clicking 'Manage Credentials' then "
                          "selecting 'Generate a New API Key' under "
                          "'Manage Tableau Credentials'",
    "TABLEAU_SECRET_KEY": "TABLEAU_SECRET_KEY: The secret key generated by "
                          "clicking 'Manage Credentials' then "
                          "selecting 'Generate a New API Key' under "
                          "'Manage Tableau Credentials'"
}

def import_python_file(filepath:str) -> dict:
    """Creates a keyring form a python file that contains keyring information

     In the past, Beiwe users have used os.environ Beiwe variables in a
        separate python file. They have then added the filepath to their
        sys.path and imported it into Python. This script allows backwards
        compatibility for those users.

    Args:
        filepath: Filepath to keyring file. For example,
            "~/Desktop/keyring_studies.py"

    Returns:
        Dict with keyring information from the python file
    """
    module_name = filepath.split(os.path.sep)[-1].split(".")[0]
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    kr = mano.keyring(None)
    for var in ['TABLEAU_ACCESS_KEY', 'TABLEAU_SECRET_KEY']:
        if var in os.environ.keys():
            kr[var] = os.environ[var]
    return kr


def validate_keyring(input_dict: dict = None) -> dict:
    """Checks to see if input_dict has an entry for each keyring value. If
    an entry does not exist, it returns a warning and adds an item to the dict.
    Args:
        input_dict: A dict with KEYRING_FIELDS values as keys. Default is None
    Returns:
        A dict with a value for each value in KEYRING_FIELDS
        """
    if input_dict is None:
        output_dict = dict()
    else:
        output_dict = input_dict
    for keyring_field in KEYRING_FIELDS:
        if keyring_field in output_dict.keys():
            continue
        logger.warning("No keyring entry for %s, creating a blank entry",
                       keyring_field)
        logger.warning("Field description: %s",
                       KEYRING_DESCRIPTIONS[keyring_field])
        output_dict[keyring_field] = ""
    logger.info("Current Keyring file:")
    for keyring_field in KEYRING_FIELDS:
        logger.info(keyring_field + ": " + output_dict[keyring_field])
    return output_dict


def write_keyring(
        filepath: str, input_dict: dict = None,
        encrypt_file: bool = False, passphrase: str = None
):
    """Writes an optionally encrypted keyring file
    Args:
        filepath: The path to write the keyring file to
        input_dict: The dictionary to write
        encrypt_file: Whether to encrypt the file
        passphrase: a passphrase to use to encrypt the file. If this is None
            and encrypt_file is True, you will be asked to input a passphrase.
            Note that this may cause your program to hang.
    Returns:
        Writes the keyring file to the filepath
"""
    input_dict = validate_keyring(input_dict)
    if encrypt_file:
        json_obj_bytes = bytes(json.dumps(input_dict, indent=3), 'utf-8')
        if passphrase is None:
            passphrase = getpass("Enter password to encrypt " + filepath + ":")
        key = cryptease.kdf(passphrase)
        cryptease.encrypt_to_file(filepath, io.BytesIO(json_obj_bytes), key)
        logger.info("Keyring file written to " + filepath)
    else:
        with open(filepath, "w") as f:
            json.dump(input_dict, f, indent=3)


def read_keyring(filepath: str,
                 passphrase: str = None) -> dict:
    """Read an optionally encrypted json or python file with keyring information
    Args:
        filepath: Filepath where keyring data is stored. This file should
            have been written by write_keyring, or it should be a python file that mano.keyring can use to make a keyring.
        passphrase: Passphrase used to decrypt the file. If this is None and
            the file is encrypted, the function will ask the user for a
            passphrase.

"""
    output_dict = dict()
    if filepath.endswith(".py"):
        return import_python_file(filepath)
    try:
        with open(filepath) as f:  # see if our file is readable
            output_dict = json.load(f)
    except UnicodeDecodeError:  # the file must be decrypted
        logger.info("File is encrypted, reading with encryption...")
        if passphrase is None:
            passphrase = getpass("Enter password to decrypt " + filepath + ":")
        try:
            with open(filepath, "rb") as fp:
                key = cryptease.key_from_file(fp, passphrase)
                decrypted_data = b""
                for chunk in cryptease.decrypt(fp, key):
                    decrypted_data += chunk
                decrypted_json = str(decrypted_data, encoding='utf-8')
                output_dict = json.loads(decrypted_json)
        except UnicodeDecodeError:  # they typed a bad password
            logger.error("Decryption failed. Perhaps you mistyped the password?")
    return output_dict


def get_data_summaries(
        study_id: str,
        output_file_path: str,
        keyring: dict = None,
        keyring_filepath: str = None,
        keyring_password: str = None,
        time_granularity: str = "daily",
        participant_ids: list = None,
        start_date: str = None,
        end_date: str = None,
        fields: list = None,
        limit: int = None
) -> pd.DataFrame:
    """
    Get Tableau data summaries from Beiwe website.

    Tableau summaries include data volume statistics as well as any forest
    statistics that are available from the Tableau API. Summaries are returned
    as a pandas dataframe and optionally written as a csv file.
    Args:
        study_id: 24-character study ID found at the top right corner of the
            study page
        output_file_path: Filepath to write an output file to. If this is None,
             no file is written.
        keyring: Keyring read by read_keyring()
        keyring_filepath: Filepath to a keyring file written by write_keyring()
        keyring_password: Password to decrypt the file at keyring_filepath if 
            the file is encrypted
        time_granularity: The time granularity of summaries, "daily" or "hourly"
        participant_ids: A list of participants you want summaries for. Enter None to pull summaries for everyone
        start_date: The first date you want summaries for, in YYYY-MM-DD format. Enter None to pull all available summaries
        end_date: The last date you want summaries for, in YYYY-MM-DD format. Enter None to pull all available summaries
        fields: The list of summary statistics you would like to pull. Enter None to pull all available summaries. A list of available summary statistics is at https://github.com/onnela-lab/beiwe-backend/wiki/Tableau-API. 
        limit: An integer corresponding to the number of rows you want to pull (for example, put 100 to pull the first 100 rows). Enter None to pull all available rows.
        

    Returns:
        Dataframe with Beiwe summary statistics pulled from the server
    """
    if keyring is None:
        if keyring_filepath is None:
            logger.error("Unable to get data summaries. "
                         "No keyring_path or keyring provided.")
            return
        else:
            keyring = read_keyring(keyring_filepath, keyring_password)
    if len(keyring) == 0:
        logger.error("Unable to read keyring file")
        return
    if len(study_id) != 24:
        logger.error("Error: Incorrect study_id input. Please "
                     "enter the 24-character study ID found in the top "
                     "right of your study page.")
        return

    url = keyring["URL"] + '/api/v0/studies/' + study_id + '/summary-statistics/' + time_granularity
    filter_dict = {"participant_ids": participant_ids,
    "start_date": start_date,
    "end_date": end_date,
    "fields": fields,
    "limit": limit
                   }
    any_filters = False
    for key in filter_dict:
        if filter_dict[key] is not None:
            any_filters = True
        
    url_addition_list = []
    if any_filters:
        for key in filter_dict.keys():
            if filter_dict[key] is None:
                continue
            if type(filter_dict[key]) is list: # for fields and participant_ids
                url_addition_list.append(
                    key + "=" + ",".join(filter_dict[key])
                )
            elif type(filter_dict[key]) is int:
                url_addition_list.append(  # for limit filter
                    key + "=" + str(filter_dict[key])
                )
            elif type(filter_dict[key]) is str:
                url_addition_list.append(  # for limit filter
                    key + "=" + filter_dict[key]
                )
            else:
                logger.warning("Incorrect type for %s. Not filtering.", key)

                continue
        url = url + "?" + "&".join(url_addition_list)

    try:
        headers = {
            'X-Access-Key-Id': keyring["TABLEAU_ACCESS_KEY"],
            'X-Access-Key-Secret': keyring["TABLEAU_SECRET_KEY"],
        }

        logger.info('Extracting data from server')
        response = requests.get(
            url,
            headers=headers)
        logger.info('Converting data to DataFrame')
        summaries_df = pd.DataFrame.from_dict(response.json())
        logger.info('Writing CSV file')
        summaries_df.to_csv(output_file_path, index = False)
        summaries_downloaded = True
    except requests.models.MissingSchema:
        logger.error("It looks like your keyring file has been set up"
              " incorrectly. Please ensure that the URL field begins"
              " with https://")
        logger.error("URL used: %s", url)
    except ValueError:
        logger.error("Something went wrong. Please ensure that you"
                     " have enabled Forest on the Beiwe website")
        return

    if summaries_df.columns[0] == "errors":
        logger.error("Error: %s. You may want to update your study ID "
                     "or your keyring file.", summaries_df["errors"][0])
    return


def ensure_time_coverage(summaries_df, time_column):
    """Helper function to ensure that there are no days between the minimum
    and maximum day in a dataframe without any rows. This insures that pivot
    functions work correctly.
    Args:
        summaries_df: A preprocessed input_summaries_df created during
            plot_heatmap
        time_column: The column indicating date.
        """
    lines_to_add = []
    max_date = summaries_df[time_column].max()
    min_date = summaries_df[time_column].min()
    # We don't want the pivot to create a NA Beiwe ID, so we'll pull one
    sample_beiwe_id = summaries_df["participant_id"].unique()[0]
    if time_column == "date":
        date_range = pd.Series(pd.to_datetime(
            pd.date_range(min_date, max_date, freq='d')
        )).dt.date
        unique_values = set(summaries_df["date"].astype(str).tolist())
    else:
        date_range = range(min_date, max_date)
        unique_values = set(
            summaries_df["days_since_start"].astype(
                int
            ).astype(str).unique().tolist()
        )

    for date in date_range:
        # If we have duplicate dates for a Beiwe ID, the pivot will go wrong
        if str(date) not in unique_values:
            lines_to_add.append(
                pd.DataFrame({"participant_id": [sample_beiwe_id],
                              time_column: [date]})
            )
    summaries_df = pd.concat([summaries_df] + lines_to_add,
                             ignore_index=True, axis=0).fillna(0)

    return summaries_df

def plot_heatmap(input_summaries_df: pd.DataFrame,
                 stream_to_plot: str,
                 output_dir: str,
                 plot_study_time: bool,
                 binary_heatmap: bool,
                 overlay_surveys: bool,
                 display_plots: bool,
                 max_ids_per_plot: int,
                 include_y_labels: bool):
    """Create a heatmap for a given data stream
    Args:
        input_summaries_df: A preprocessed input_summaries_df created during
            data_volume_heatmaps
        stream_to_plot: Data Stream to plot
        output_dir: Directory to write data volume plot .png files to. If this
            is None, no plots will be saved.
        plot_study_time: Whether to make data volume plots based on study time.
            If True, the X axis is days since the participant entered the
            study. If False, the X axis is the date of data collection.
        binary_heatmap: Whether to make data volume binary (either any data or
            no data) before plotting.
        overlay_surveys: Whether to display dashes indicating survey
            submissions over data volume.
        display_plots: Whether to display plots produced by the function
        max_ids_per_plot: Maximum number of Beiwe IDs on a plot. If
            summaries_df has more than this many Beiwe IDs, it will break
            the plot up
        include_y_labels: Whether to include y labels with participant IDs on the plot.

    """

    os.makedirs(output_dir, exist_ok = True)

    summaries_df = input_summaries_df.copy()
    # We want to plot the first column that matches our data stream.
    col_to_plot = [col for col in summaries_df.columns
                   if col.find(stream_to_plot) > 0][0]
    if plot_study_time:
        time_column = "days_since_start"
    else:
        time_column = "date"

    if overlay_surveys: # We need to get survey submissions before we filter
        # out unnecessary rows because some rows may have a survey submission
        # but no non-zero data volume value.
        surveys_df = summaries_df.loc[
            summaries_df["any_survey_submission"] > 0,
            ["participant_id", time_column]
        ].reset_index(drop = True)

    # We only want to show users for which there is at least one non-zero value
    summaries_df = summaries_df.loc[summaries_df[col_to_plot] > 0]
    if summaries_df.shape[0] == 0:
        logger.error("Error: No data volume of type %s found", stream_to_plot )
        return

    summaries_df = ensure_time_coverage(summaries_df, time_column)
    if binary_heatmap:
        summaries_df[col_to_plot] = (
                summaries_df[col_to_plot] > 0
        ).astype(float)
    else:  # otherwise, convert this to Megabytes
        summaries_df[col_to_plot] = summaries_df[col_to_plot] / 1000000

    df_to_plot = summaries_df.pivot(
        index="participant_id", columns=time_column,
        values=col_to_plot
    ).fillna(0)

    df_to_plot["sums"] = df_to_plot.sum(axis=1)
    df_to_plot.sort_values("sums", ascending=False, inplace=True)

    if binary_heatmap:
        volume_string = "days"
        xlab_addition = ("\n\n Days in black indicate that a user collected "
                         "some data that day.")
    else:
        volume_string = "MB"
        xlab_addition = ("\n\n Days in darker shades of grey indicate that a"
                         " user collected more data.")

    survey_y = []
    survey_x = []
    if overlay_surveys:  # in order to overlay the surveys on the heat map, we
        # have to figure out which list index corresponds to which value in
        # the surveys.
        surveys_df = surveys_df.loc[
            surveys_df["participant_id"].isin(df_to_plot.index) &
            surveys_df[time_column].isin(df_to_plot.columns),:
            ]
        survey_y = [df_to_plot.index.tolist().index(participant_id)
                    for participant_id in surveys_df["participant_id"]]
        survey_x = [df_to_plot.columns.tolist().index(time_val)
                    for time_val in surveys_df[time_column]]
        xlab_addition += ("\nTurquoise dashes indicate that a survey "
                          "was taken that day.")


    y_label_df = pd.DataFrame(
        {"participant_id": df_to_plot.index,
         "sums": df_to_plot["sums"]}
    )
    y_label_df["rank"] = y_label_df["sums"].rank(ascending=False)

    y_label_df["left_axis"] = (
            y_label_df["participant_id"]
            + " ("
            + y_label_df["rank"].astype(int).astype(str)
            + "; "
            + y_label_df["sums"].round().astype(int).astype(str)
            + " "
            + volume_string
            + ")")
    # Change the index so that the added data will show up as y labels
    # in the plot.
    df_to_plot.index = y_label_df["left_axis"]
    df_to_plot.drop("sums", axis=1, inplace=True)
    # Now, we need to automatically space X axis ticks.
    num_x_ticks = 10
    num_y_ticks = 5
    if df_to_plot.shape[1] <= num_x_ticks:
        x_axis = df_to_plot.columns
    else:
        x_axis = [""] * df_to_plot.shape[1] #nothing on everywhere except the
        # spots we want x ticks
        spacing_between_ticks = df_to_plot.shape[1] / (num_x_ticks - 1)
        for i in range((num_x_ticks - 1)):
            index_to_show = np.min([round(i * spacing_between_ticks), len(x_axis) - 1])
            x_axis[index_to_show] = df_to_plot.columns[index_to_show]
        x_axis[-1] = df_to_plot.columns[-1]
    if include_y_labels:
        y_axis = df_to_plot.index
    else:
        y_axis = [""] * df_to_plot.shape[0]  # nothing on everywhere except the
        # spots we want y ticks
        spacing_between_ticks = df_to_plot.shape[0] / (num_y_ticks - 1)
        for i in range((num_y_ticks - 1)):
            index_to_show = np.min([round(i * spacing_between_ticks), len(y_axis) - 1])
            y_axis[index_to_show] = index_to_show + 1
        y_axis[-1] = df_to_plot.shape[0]

    if binary_heatmap:
        plot_type = "binary"
    else:
        plot_type = "volume"
    if output_dir is not None:
        output_filename = (stream_to_plot + "_by_" + time_column + "_"
                           + plot_type + ".png")
        save_path = os.path.join(output_dir, output_filename)
    else:
        save_path = None

    plot_title = stream_to_plot.replace("_", " ").title() + " Data Volume Plot"

    if df_to_plot.shape[0] > max_ids_per_plot:
        for i in range(int(np.floor(df_to_plot.shape[0]/ max_ids_per_plot))):
            plot_number = str(i + 1)
            logger.info("Creating plot "+ plot_number)
            current_plot_title = plot_title + " " + plot_number
            current_save_path = save_path.replace(".png", plot_number + ".png")
            max_index = np.min([(i+1)*max_ids_per_plot, df_to_plot.shape[0]])
            current_df = df_to_plot.iloc[i*max_ids_per_plot:max_index, :]
            colsums = pd.Series(
                current_df.sum(axis=0)
            ).reset_index(drop = True)
            min_col = colsums.loc[colsums > 0].index.min()
            max_col = colsums.loc[colsums > 0].index.max()
            current_df = current_df.iloc[:, min_col:max_col]
            current_x_axis = x_axis[min_col:max_col]
            create_save_plot(current_df,
                             current_x_axis, survey_x, survey_y, xlab_addition,
                             plot_study_time, display_plots, current_save_path,
                             current_plot_title, include_y_labels, y_axis)
    else:
        create_save_plot(df_to_plot, x_axis, survey_x, survey_y, xlab_addition,
                         plot_study_time, display_plots, save_path, plot_title,
                         include_y_labels, y_axis)




def create_save_plot(df_to_plot, x_axis, survey_x, survey_y,
                     xlab_addition, plot_study_time,display_plots,
                     save_path, plot_title, include_y_labels, y_axis):
    """Helper function used to create and save a plot"""
    if include_y_labels:
        plot_height = int(np.round(df_to_plot.shape[0] / 2)) #we need space for each label
    else:
        plot_height = 6 #for easier viewing on laptops

    plot_width = 10

    fig, ax = plt.subplots(figsize=(plot_width, plot_height))  # width, height
    plt.set_cmap('Greys')
    im = ax.imshow(df_to_plot, aspect="auto", interpolation='none')
    ax.set_xticks(np.arange(df_to_plot.shape[1]), labels=x_axis, rotation=25,
                  horizontalalignment='right')
    ax.set_yticks(np.arange(df_to_plot.shape[0]), labels=y_axis)
    ax.scatter(survey_x, survey_y, marker="_", c="#33b3a6", label="Survey")
    if include_y_labels:
        plt.ylabel("Beiwe ID, rank, and total volume")
    else:
        plt.ylabel("Rank")
    if plot_study_time:
        plt.xlabel("Days Since Registration" + xlab_addition)
    else:
        plt.xlabel("Date" + xlab_addition)
    plt.title(plot_title)
    try:
        fig.tight_layout()
        plt.tight_layout()
    except ValueError:
        logger.error("Plot is too big. Please retry doing the plot with"
                     " fewer Beiwe IDs")
    except np.linalg.LinAlgError:
        logger.error("Unable to create plot for %s because there's not enough data", plot_title)
        return
    if save_path is not None:
        plt.savefig(save_path, pad_inches=1, facecolor="white",
                    edgecolor="white")
    if display_plots:
        plt.show()
    plt.close()


def data_volume_plots(
        data_summaries_path: str = None, output_dir: str = "data_volume_plots",
        display_plots: bool = True, data_streams_to_plot: list = None,
        users_to_include: list = None, start_date: str = None,
        end_date: str = None, max_study_days: int = None,
        binary_heatmap: bool = True, plot_study_time: bool = True,
        max_ids_per_plot: int = 1000,
        overlay_surveys: bool = False,
        include_y_labels: bool = True
):
    """Create data volume summary plots for a study

    This function creates data volume summary plots for a given study,
        optionally displays them to the user, and optionally writes them to a
        directory.
    This function first checks to see if a data volume summaries file exists
        at data_summaries_path. If a summary does not exist at the path, it
        attempts to create one using forest.aspen.get_data_summaries.
        Several parameters are exposed to customize plotting.

    Args:
        data_summaries_path: Path to data summaries csv file. Output of
            forest.aspen.get_data_summaries. If this is not available, the
            function will attempt to generate such a file
        output_dir: Directory to write data volume plot .png files to. If this
            is None, no plots will be saved.
        display_plots: Whether to display plots produced by the function
        data_streams_to_plot: List of data streams to plot. If this is None,
            all data streams with a current Forest tree will have plots
            generated.
        users_to_include: List of Beiwe IDs of users to include in data volume
            plots.
        start_date: Earliest date of data to include in data volume summary
            plots, in YYYY-MM-DD format.
        end_date: Latest date of data to include in data volume summary
            plots, in YYYY-MM-DD format.
        max_study_days: Maximum number of study daya for a user. If a user has
            data volume collected more than max_study_days after registration,
            data past that period will not be displayed.
        binary_heatmap: Whether to make data volume binary (either any data or
            no data) before plotting.
        plot_study_time: Whether to make data volume plots based on study time.
            If True, the X axis is days since the participant entered the
            study. If False, the X axis is the date of data collection.
        overlay_surveys: Whether to display dashes indicating survey
            submissions over data volume.
        max_ids_per_plot: Maximum number of Beiwe IDs on a plot. If
            summaries_df has more than this many Beiwe IDs, it will break
            the plot up
        include_y_labels: whether to include Beiwe IDs as y labels in the plot
    """

    summaries_df = pd.read_csv(data_summaries_path)

    
    if summaries_df.shape[0] == 0:
        logger.error("Error: No data volume summaries data found")
        return
    if data_streams_to_plot is None:
        data_streams_to_plot = DATA_STREAMS_WITH_FOREST_TREES


    summaries_df.fillna(0, inplace = True)
    summaries_df["date"] = pd.to_datetime(summaries_df["date"]).dt.date
    # Some people have data volume days in 1969. We want to get rid of this
    # so we don't screw up our plots.
    summaries_df = summaries_df.loc[
        summaries_df["date"] > pd.to_datetime(BACKFILL_START_DATE),:
    ]
    summaries_df["min_date"] = summaries_df.groupby("participant_id")[
        "date"
    ].transform("min")
    summaries_df["days_since_start"] = (summaries_df["date"]
                                        - summaries_df["min_date"]).dt.days
    if overlay_surveys:
        summaries_df["any_survey_submission"] = (
            summaries_df["beiwe_survey_answers_bytes"] +
            summaries_df["beiwe_audio_recordings_bytes"]
        ) > 0
    else:
        summaries_df["any_survey_submission"] = 0
    if start_date is not None:
        start_datetime = pd.to_datetime(start_date)
        summaries_df = summaries_df.loc[summaries_df["date"] > start_datetime]
    if end_date is not None:
        end_datetime = pd.to_datetime(end_date)
        summaries_df = summaries_df.loc[summaries_df["date"] < end_datetime]
    if max_study_days is not None:
        summaries_df = summaries_df.loc[
            summaries_df["days_since_start"] <= max_study_days
        ]
    if users_to_include is not None:
        summaries_df = summaries_df.loc[
            summaries_df["participant_id"].isin(users_to_include),:
        ]

    for stream_to_plot in data_streams_to_plot:
        plot_heatmap(summaries_df, stream_to_plot, output_dir,
                     plot_study_time, binary_heatmap, overlay_surveys,
                     display_plots, max_ids_per_plot, include_y_labels)


def get_num_users(summaries_df=None, summaries_path=None, data_streams=None):
    """Get the number of users that has at least one day with a data stream
     as a dataframe
     Args:
         summaries_df: Dataframe of data volume summaries
         summaries_path: path to csv of data volume summaries
         data_streams: list of data streams to get summaries for. If not
            specified, only data streams with forest trees will have statistics
            listed.
    Returns:
        Dataframe with a row for each thing in data_streams and a column saying
        how many people have non-zero days.
     """
    if summaries_df is None and summaries_path is not None:
        summaries_df = pd.read_csv(summaries_path)
    else:
        logger.error("Summaries dataframe not included")
    if data_streams is None:
        data_streams = DATA_STREAMS_WITH_FOREST_TREES
    num_users_list = []
    summaries_df = summaries_df.fillna(0)
    for stream in data_streams:
        col_name = "beiwe_" + stream + "_bytes"
        num_users_list.append(summaries_df.loc[summaries_df[col_name] > 0, "participant_id"].nunique())

    return pd.DataFrame({"Data Type": data_streams, "Number of Users": num_users_list})


