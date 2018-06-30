import glob
import os
import datetime

try:
    import mano
    import logging
    import mano.sync as msync
except:
    print("Failed importing nano. This needs to be run in a pipenv environment to work.")


def download_beiwe_data(study_no=2, output_folder= "/tmp/beiwe-data", time_end=None, time_start=None):
    """
    Download Beiwe data to a local directory. If time_start is not specified, extraction will
    proceed one week from time_end. If time_end is not specified, today's date is use as default.

    Args:
        study_no (int): Study number 1-3
        output_folder (str): Downloaded data will be stored here
        time_end (str): End date of extraction in the format YYYY-MM-DD
        time_start (str): Start date of extraction in the format YYYY-MM-DD

    Returns:
        active_users (list): List of users for whom directories were returned
    """

    # specify keyring and data streams
    Keyring = mano.keyring("beiwe.onnela")
    data_streams = ["power_state", "survey_answers"]
    logging.basicConfig(level=logging.INFO)

    # choose study
    studies = {1: ("UCSD_Little_UNI_HIV_Pos", "5a3a856203d3c42e31329970"), \
               2: ("UCSD_Little_UNI_HIV_Neg", "5a3a85db03d3c42e3132998a"), \
               3: ("UCSD_Little_RDS Study", "5a3a862503d3c42e3217bb90")}
    (study_name, study_id) = studies[study_no]
    print("  Processing study %s (study ID %s)." % (study_name, study_id))

    # specify time_end
    if time_end is None:
        time_end = datetime.datetime.today().strftime("%Y-%m-%d") + "T00:00:00"
    else:
        if len(time_end) == 10:
            time_end = time_end + "T00:00:00"

    # specify time_start
    if time_start is None:
        end_time = datetime.datetime.strptime(time_end, "%Y-%m-%dT%H:%M:%S") 
        start_time = end_time - datetime.timedelta(days=7)
        time_start = start_time.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        if len(time_start) == 10:
            time_start = time_start + "T00:00:00"
    print("  Extracting data from %s to %s to %s." % (time_start, time_end, output_folder))

    # loop over all user IDs in the system for the study and download data
    for user_id in mano.users(Keyring, study_id):
        print("  Downloading data for user %s." % user_id)
        zf = msync.download(Keyring, study_id, user_id, data_streams=data_streams, time_start=time_start, time_end=time_end)
        zf.extractall(output_folder)

    # identify users for whom we have any data (folder exists)
    active_users = os.listdir(output_folder)
    active_users.remove("registry")
    print("\n  Found data for the following users:")
    for user_id in active_users:
        print(" ", user_id)
    return active_users


def check_file_size(data_dir, dates, subjects, surveys, data_stream_indices):
    """
    Function to loop over all specified dates, subjects, data streams and surveys.
    Prints out the file sizes for each.

    Args:
        data_dir (str): Location of the directory called "data" as downloaded from Beiwe
        dates (list): List of dates to check
        subjects (list): List of Beiwe subject IDs to check
        surveys (list): List of Beiwe survey IDs to check
        data_stream_indices (list): List of integers corresponding to data types to check

    """

    data_streams = ["accelerometer", "bluetooth", "calls", "gps", "identifiers", \
                "app_log", "power_state", "survey_answers", "survey_timings", \
                "texts", "audio_recordings", "wifi", "proximity", "gyro", \
                "magnetometer", "devicemotion", "reachability", "ios_log", "image_survey"]

    for date in dates:
        print("Date:", date)
        print("-----------------")
        for subject in subjects:
            print("Subject:", subject)

            # passive data files
            for data_stream_index in data_stream_indices:
                path = data_dir + subject + "/" + data_streams[data_stream_index] + "/" + date + "*"
                files = glob.glob(path)
                total_size = 0
                for file in files:
                    total_size += os.path.getsize(file)
                print("  %s total file size is %d bytes." % (data_streams[data_stream_index], total_size))

            # survey files
            for survey in surveys:
                path = data_dir + subject + "/survey_answers/" + survey + "/" + date + "*"
                files = glob.glob(path)
                total_size = 0
                for file in files:
                    total_size += os.path.getsize(file)
                print("  %s survey total file size is %d bytes." % (survey, total_size))
            print("")
        print("")



def parse_survey_responses():
    """
    Beiwe survey responses are separated by semicolons. Because survey answers are stored
    in CSV files, all commas are converted into semicolons. This presents a problem 
    for parsing however when questions contains commas. A more sophisticated fix would
    require reading in the JSON file of questions, but this approach also works provided one is 
    happy to construct the question_answer dictionary manually. This example is for the PIRC study.

    """
    
    question_answer_dictionary = {"What best describes your relationship to the new sexual \
    partners reported in the last week? (check all that apply):" : ["Unknown person - someone \
    you have never met before", "One-time partner - someone you knew previously and had sex \
    with one time", "Repeat partner (non-main) - someone you had sex with more than once \
    but is not primary sexual partner (e.g. not a boyfriend; wife; etc.)", "Trade partner - \
    someone who gave sex or received sex from in exchange for money or other goods"]}

    datafile = "2018-04-13 17_43_23.csv"

    line_count = 0
    for line in open(datafile):
        if line_count > 0:
            line = line.rstrip().split(",")
            question = line[2]
            answer = line[4]
            output = []
            if question in question_answer_dictionary:
                for (ind, option) in enumerate(question_answer_dictionary[question]):
                    if option in answer:
                        output.append(ind)
            if output:
                print(question, output)
            else:
                print(question, answer)
        line_count += 1




