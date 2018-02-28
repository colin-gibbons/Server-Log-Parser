from urllib.request import urlopen
import os
import re
import datetime
import json

# Constant Vars
url = "https://s3.amazonaws.com/tcmg476/http_access_log"
fileName = "http.log"
monthName = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'} # Maps month num (key) to name (value)

# Downloads http log to "http.log"
def getDataFile(): 
    with open(fileName, 'wb') as logFile: # creates a new http.log file
        with urlopen(url) as stream: # connect to server
            fileSize = stream.length

            # https://stackoverflow.com/questions/22676/how-do-i-download-a-file-over-http-using-python
            print("Downloading \"%s\" (%s KB)..." % (fileName, fileSize / 1000))

            currentFileSize = 0
            blockSize = 8192
            while True: # loop through download (blockSize at a time), and write bytes to file
                buffer = stream.read(blockSize)
                if not buffer: # if at end of file
                    break

                currentFileSize += len(buffer) # track how many bytes downloaded so far
                logFile.write(buffer)
                status = r"%10d [%3.2f%%]" % (currentFileSize, currentFileSize*100. / fileSize) # displays percentage downloaded
                status = status + chr(8)*(len(status) + 1)

                print(status, end="") # prints without appended "\n"
            
            print("", end="\n") # reset print appended char

# Sorts logs by month, and then by day in the "data" dictionary.  
def parseLogs(data):
    with open(fileName, 'r') as logFile: #opens http.log file
        print("Parsing Data File...")

        monthNum = {v: k for k, v in monthName.items()}  # maps Month name (key) to num (val), generated by inverting the key/val pairs of monthInt
        currline = 0
        badParses = [] # list of all failed parses
        for line in logFile: # iterate through entire log file
            currline += 1 
            splitData = re.split('.*\[(.*?):.*\] \".* (.*) .*\" (\d{3})', line)

            if len(splitData) == 5: # If regex worked:
                dateSplit = splitData[1].split('/') # splits up day/month/year string
                date = datetime.date(int(dateSplit[2]), monthNum[dateSplit[1]], int(dateSplit[0])) # create date object (year, month, day)
                
                logData = {'date': date, 'name':splitData[2], 'code':int(splitData[3])} # store each log as a dict #TODO: Add key for all data

                if date.day in data[date.month]: # if logs list has already been created for that day
                    data[date.month][date.day].append(logData) # append dictionary containing log data
                else:
                    data[date.month][date.day] = [logData] # otherwise add to month dictionary, key = day, value = logData
            else: # If regex didn't work:
                badParses.append(splitData) # add to list of failures

        print(str(len(badParses)) + " lines couldn't be parsed.") #TODO: save bad parses to file

def countEvents(month):
    sum = 0
    for dayNum, logs in month.items():
        sum += len(logs)
    return sum
 

def main():
    data = {x:{} for x in range(1,13)}  # generates a dictionary containing 12 empty dictionaries (one for each month of data),
                                        # key = monthNum, value = dictionary of events on each day

    if not os.path.exists(fileName):  # check if file exists before re-downloading
        print("No cached " + fileName + " found.\nDownloading from: " + url)
        getDataFile() # Saves file as http.log
    else:
        print("Using cached " + fileName + " file.")
       
    parseLogs(data) # parses data file, and sorts by month and day

    print("Events Per Month/Day/Week:")

    successCode = 0
    errorCode = 0
    elsewhereCode = 0

    fileNames = {} # tracks how many times each file name was referenced
    weeklyLogs = {}

    # Main loop - goes through data dictionary, keeping track of stats
    for monthNum, month in data.items(): # for each dictionary in data
        print("\n" + monthName[monthNum] + ": [" +str(countEvents(month)) + " total events]") # prints name of month & how many events occurred
        for dayNum, logs in month.items(): # iterate through each day of logs
            print("\t" + str(dayNum) + " - " + str(len(logs)) + " events")
            for log in logs: # iterate through each log dictionary contained in the logs list
                
                # track http codes
                logCode=log['code']
                if logCode <= 299:
                    successCode+=1
                elif 300 <= logCode <= 399:
                    elsewhereCode+=1
                else: #logCode >= 400
                    errorCode+=1

                # track file names
                if log["name"] in fileNames:
                    fileNames[log["name"]] += 1
                else:
                    fileNames[log["name"]] = 1 
                
                # track logs per week
                if log["date"].isocalendar()[1] in weeklyLogs:
                    weeklyLogs[log["date"].isocalendar()[1]] += 1
                else:
                    weeklyLogs[log["date"].isocalendar()[1]] = 1

    sorted_weeklyLogs = sorted(weeklyLogs.items(), key=lambda x: x[0])
    print("\nRequests per week: ")
    for weekNum, count in sorted_weeklyLogs:
        print("\t" + str(weekNum) + " - " + str(count) + " events")

    total_codes = float(successCode + errorCode + elsewhereCode)
    print("\nTotal Requests: " + str(int(total_codes)))
    print("\nPercentage failure (4xx): {0:.4g} %".format(((errorCode / total_codes) * 100.0)))
    print("Percentage redirected (3xx): {0:.4g} %".format(((elsewhereCode / total_codes) * 100.0)))

    sorted_fileNames = sorted(fileNames.items(), key=lambda x: x[1]) # Sort fileNames dict by file count
    print("\nMost requested file: " + sorted_fileNames[-1][0] + " (accessed " + str(sorted_fileNames[-1][1]) + " times)")
    print("Least requested file: " + sorted_fileNames[0][0] + " (accessed " + str(sorted_fileNames[0][1]) + " time)")

    print("\nCreating .json files...")

    for monthNum in range(1,13):
        with open(monthName[monthNum] + ".json", 'w') as outfile:
            json.dump(data[monthNum], outfile,  default=str)


if __name__ == "__main__":
    main()