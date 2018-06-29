##5/15/18##
##Emily Huang##

##Objective of this code##

##To plot call data at the daily level for each subject, including number of calls, number of 
##unique callers, and length of calls, separately for incoming, outgoing, and missed calls

##Study is still ongoing: data was downloaded on 5/15/18

#################################################################################################
##Packages##
#################################################################################################

library(dplyr)
library(tidyr)

#################################################################################################
##Directories##
#################################################################################################

##Clear the workspace
rm(list=ls())

##The folder with all the subjects' data (the subfolders are named by the patient ID's)
data_filepath <- "~/Documents/data/Ariadne/data"

#################################################################################################
##Demographic data and key dates (entry to study, date of surgery)##
#################################################################################################

subjectInfo <- read.csv("~/Documents/data/Ariadne/studyDocuments/android_patients_notesOmitted.csv")

#################################################################################################
##Read in call data##
#################################################################################################

##We gather all the call data from the study into a single data frame that has
##the following columns:
##

##This code assumes that the participant is in the EST time zone.

read_calls <- function(){
  ##This list will have a lot of elements, one for each hour of call data in the study 
  data_list <- list()
  
  ##Vector of patient names
  patient_names <- list.files(data_filepath)
  
  ##Now we loop through the patients in the study
  for(patient_name in patient_names){
    
    ##The files that contain the call data for the specific patient
    call_files <- list.files(paste(data_filepath, patient_name, "calls", sep="/"))
    
    ##Loop through the call files of the specific patient
    for(call_file in call_files){
      ##Read the data in call_file
      hour_data <- read.csv2(paste(data_filepath, patient_name,"calls",call_file,sep="/"), sep=",")
      
      ##Add the patient's Beiwe ID as a column
      hour_data[,"patient"] <- patient_name
      
      ##Add the date (assuming EST time zone) as another column
      Date <- as.POSIXct(gsub("T", " ", hour_data[,"UTC.time"]), format = "%Y-%m-%d %H:%M:%S", tz = "GMT")
      Date <- format(Date, tz = "America/New_York") ##convert from UTC to EST time
      hour_data[,"Date"] <- as.Date(Date)
      
      ##Make the data an element in data_list
      data_list[[paste(patient_name, call_file)]] <- hour_data
    }
    
  }
  
  ##Concatenate the elements of data_list (i.e., getting all the call data from the study
  ##into a single data frame)
  data <- do.call(rbind, data_list)
  rownames(data) <- 1:nrow(data)  
  
  ##Output the data frame
  return(data)
}

data <- read_calls()

##You can ignore warnings of the type:
##In read.table(file = file, header = header, sep = sep,  ... :
##incomplete final line found by readTableHeader on .......


#################################################################################################
##Compute statistics from the call data##

##The statistics include the following:
##number of calls, number of unique callers, and length of calls per day
##for incoming, outgoing, and missed calls
#################################################################################################

##Vector of patient names
patient_names <- list.files(data_filepath)

data[,"call.type"] <- as.character(data[,"call.type"])

##For each patient, on each type, for each type of call (incoming, outgoing, missed), 
##we compute the number of calls, total length in seconds, and the number of unique phone
##numbers
daily_data <- data %>% 
  group_by(patient, Date, call.type) %>%
  dplyr::summarize(
    total_calls = n(),
    total_seconds = sum(duration.in.seconds),
    unique_calls = length(unique(hashed.phone.number))
  ) %>% ungroup %>% data.frame

##We reshape the daily_data data frame to a wide format, with just one row per date for
##each patient
spread_calls   <- daily_data %>% dplyr::select(c(patient, Date, call.type, total_calls)) %>% spread(call.type, total_calls)
spread_seconds <- daily_data %>% dplyr::select(c(patient, Date, call.type, total_seconds)) %>% spread(call.type, total_seconds)
spread_uniques <- daily_data %>% dplyr::select(c(patient, Date, call.type, unique_calls)) %>% spread(call.type, unique_calls) 

colnames(spread_calls)[which(colnames(spread_calls) == "Incoming Call")] <- "Number_of_Incoming_Calls"
colnames(spread_calls)[which(colnames(spread_calls) == "Outgoing Call")] <- "Number_of_Outgoing_Calls"
colnames(spread_calls)[which(colnames(spread_calls) == "Missed Call")]   <- "Number_of_Missed_Calls"
colnames(spread_seconds)[which(colnames(spread_seconds) == "Incoming Call")] <- "Total_Incoming_Seconds"
colnames(spread_seconds)[which(colnames(spread_seconds) == "Outgoing Call")] <- "Total_Outgoing_Seconds"
colnames(spread_seconds)[which(colnames(spread_seconds) == "Missed Call")]   <- "Total_Missed_Seconds"
colnames(spread_uniques)[which(colnames(spread_uniques) == "Incoming Call")] <- "Number_of_Unique_Incoming_Callers"
colnames(spread_uniques)[which(colnames(spread_uniques) == "Outgoing Call")] <- "Number_of_Unique_Outgoing_Call_Recipients"
colnames(spread_uniques)[which(colnames(spread_uniques) == "Missed Call")]   <- "Number_of_Unique_Missed_Callers"

summarized_calls_data <- full_join(spread_calls, spread_seconds, by = c("patient", "Date")) %>%
  full_join(spread_uniques, by = c("patient", "Date"))

rm(daily_data, spread_calls, spread_seconds, spread_uniques)

##Convert length of call from seconds to minutes
summarized_calls_data$Total_Incoming_Minutes <- summarized_calls_data$Total_Incoming_Seconds/60
summarized_calls_data$Total_Missed_Minutes <- summarized_calls_data$Total_Missed_Seconds/60
summarized_calls_data$Total_Outgoing_Minutes <- summarized_calls_data$Total_Outgoing_Seconds/60

##Remove columns about total length in seconds
summarized_calls_data %<>% select(-c(Total_Incoming_Seconds,Total_Outgoing_Seconds,Total_Missed_Seconds)) %>% data.frame

##Compute average length of call, in minutes (some of these will involve dividing NA/NA = NA, which we will now replace with zero)
summarized_calls_data$Average_Incoming_Call_Length_in_Minutes <- summarized_calls_data$Total_Incoming_Minutes/summarized_calls_data$Number_of_Incoming_Calls
summarized_calls_data$Average_Missed_Call_Length_in_Minutes <- summarized_calls_data$Total_Missed_Minutes/summarized_calls_data$Number_of_Missed_Calls
summarized_calls_data$Average_Outgoing_Call_Length_in_Minutes <- summarized_calls_data$Total_Outgoing_Minutes/summarized_calls_data$Number_of_Outgoing_Calls

##Fill in NA's with zeroes
##An NA for, e.g., outgoing, indicates that there were no outgoing calls on that day for that patient, but
##there were one or more calls of another type (incoming or missed)
summarized_calls_data[is.na(summarized_calls_data)] <- 0

data_list <- list()
for (patient_name in patient_names){
  print(patient_name)
  ##In this loop, we do the following:
  
  ##Get first and last date with the app on phone. These dates will be used as the 
  ##time range in the subject's plots
  
  ##Some dates between the first and last date may not be in the summarized_call_data data frame
  ##because there were no incoming, outgoing, or missed calls on that date. We 
  ##will add those dates with 0's for all the call statistics
  
  sub_data <- subset(summarized_calls_data, patient == patient_name)
  
  if (nrow(sub_data) > 0){
    ##First date: take it from subject's identifiers file (first file if there are multiple)
    identifier_Files <- list.files(paste(data_filepath, patient_name, "identifiers", sep="/"))
    identifiers <- read.csv2(paste(data_filepath, patient_name,"identifiers", identifier_Files[1], sep="/"), sep = ",")
    firstDate <- as.character(identifiers$UTC.time)
    
    ##Getting first date in EST time zone
    firstDate <- as.POSIXct(gsub("T", " ", firstDate), format = "%Y-%m-%d %H:%M:%S", tz = "GMT")
    firstDate <- format(firstDate, tz = "America/New_York") ##convert from UTC to EST time
    firstDate <- as.Date(firstDate)
    
    #print(firstDate)
    
    ##Last date: look at all the subject's directories (except survey date/timings) and find the latest date
    ##for each directory
    directories <- list.files(paste(data_filepath, patient_name, sep="/"))
    directories <- setdiff(directories, c("survey_answers", "survey_timings"))
    nDirectories <- length(directories)
    lastDate <- rep(NA, nDirectories)
    
    for (i in 1:nDirectories){
      files <- list.files(paste(data_filepath, patient_name, directories[i], sep="/"))
      lastDate[i] <- tail(files, n = 1)
      rm(files)
    }
    
    ##Converting dates to EST time zone
    lastDate <- gsub(".csv","", lastDate)
    lastDate <- gsub("_", ":", lastDate)
    lastDate <- as.POSIXct(gsub("T", " ", lastDate), format = "%Y-%m-%d %H:%M:%S", tz = "GMT")
    lastDate <- format(lastDate, tz = "America/New_York") ##convert from UTC to EST time
    lastDate <- as.Date(lastDate)
    
    ##Get the latest date among all the directories
    lastDate <- max(lastDate)  
    
    #print(lastDate)
    
    ##Add zeroes for dates within the range but not in sub_data
    datesInRange <- seq(firstDate, lastDate, by = "days")
    datesInRange <- data.frame(patient = patient_name, Date = datesInRange)
    datesInRange$patient <- as.character(datesInRange$patient)
    sub_data$patient <- as.character(sub_data$patient)
    sub_data <- full_join(sub_data, datesInRange, by = c("patient", "Date"))
    sub_data[is.na(sub_data)] <- 0
    sub_data <- sub_data[order(sub_data$Date),]
    
    ##Add patient's expanded data frame to data_list
    data_list[[patient_name]] <- sub_data
    
    rm(sub_data, firstDate, lastDate, identifiers, identifier_Files, datesInRange)
  }
  
}

##Concatenate elements of data_list, so that now summarized_calls_data has the
##full range of dates for each patient's Beiwe followup
summarized_calls_data <- do.call(rbind, data_list)


#################################################################################################
##Plots of one person's call data##
#################################################################################################

##Vector of statistics that we would like to plot
covariates <- c("Number_of_Incoming_Calls",
                "Number_of_Outgoing_Calls")

patient_name <- "sf4le6yh"
par(mfrow=c(1,2))

##Focus on call summary data for the specific patient
sub_data <- subset(summarized_calls_data, patient == patient_name)

##Get the surgery date of that patient
surgeryDate <- subjectInfo$Surgery.Date[subjectInfo$Beiwe.ID == patient_name]
surgeryDate <- as.Date(surgeryDate, format = "%m/%d/%y")

##Compute the number of days since surgery
sub_data$DaysSinceSurgery <- sub_data$Date - surgeryDate

if (nrow(sub_data) > 0){
  for(covariate in covariates){
    plot(sub_data[,"DaysSinceSurgery"],sub_data[,covariate],
         type = "l",
         col = "blue",
         xlim = c(-28,56), ##4 weeks prior, to 8 weeks after surgery
         ylim = range(sub_data[sub_data$DaysSinceSurgery <= 56 &
                                 sub_data$DaysSinceSurgery >= -28,covariate]),
         xlab = "Time (days)",
         ylab = "Call count",
         #xaxs = "i",
         #yaxs = "i",
         main = paste(gsub("_"," ",covariate), sep = "")
    )
    
    ##Draw a dotted red line at surgery date
    abline(v = 0, col = "red", lwd = 2, lty = 2)
    
    ##Draw a dotted grey line at every seven day mark before and after surgery
    abline(v = 7 * setdiff(-52:52,0), col = "grey", lty = 2)
    
  }
  
  
}



