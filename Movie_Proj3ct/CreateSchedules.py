import pandas as pd
import numpy as np
import datetime
from datetime import timedelta

import os
import re

import movieModel

def CheckSchedules():



      # Grabs all of the subdirectories of DataIn as DirEntry list.  We want to make sure that there is a schedule generated that is associated with each of these folders.
    cinemaSFP = [f for f in os.scandir("DataIn") if (f.is_dir() & (f.name != ".ipynb_checkpoints"))]
    
    # Grabs all of the csv files in the folder Schedules...
    oldSchedules = [f.name for f in os.scandir("Schedules") if f.is_file() & bool(re.search(".*\.csv$", f.name))]
    
    # For each subdirectory of DataIn, see if there is a schedule already made.  If not, create one.
    for f in cinemaSFP:
        if f.name + "_Schedule.csv" not in oldSchedules:
            theatreBookingDF = pd.read_csv(f.path + "/Theatre_Bookings.csv")
            theatreDetailsDF = pd.read_csv(f.path + "/Theatre_Details.csv")
            movieModel.GenerateSchedule(theatreBookingDF, theatreDetailsDF).to_csv("Schedules/" +f.name +"_Schedule.csv", index = False)
    
    return None

if __name__ == '__main__':
    CheckSchedules()