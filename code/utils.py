import glob
import os


def check_file_size(data_dir, dates, subjects, surveys, data_stream_indices):
    """
    Function to loop over all specified dates, subjects, data streams and surveys.
    Prints out the file sizes for each.

    Args:
        data_dir (str): Location of the directory called "data" as downloaded from Beiwe
        dates (list): List of dates to check
        subjects (list): List of Beiwe subject IDs to check
        surveys (list): List of Beiwe survey IDs to check
        data_stream_indices (list): List of integers corresponding to different data types to check

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




