# Jerry Day
# 1/25/20 Redo... 2/19/2020
# BZAN 544

# Movie Project prep
# 1) Create an LP model using pyomo  <-- this part!
# 2) Create am app to see schedule(s) <-- not here.

import pandas as pd
import numpy as np
import datetime
from datetime import timedelta
from pyomo.environ import *


def GenerateSchedule(bookingDF, 
                     detailsDF, 
                     TUsize = 15, 
                     startTime = datetime.datetime.strptime("01/26/20 13:00:00", '%m/%d/%y %H:%M:%S'), 
                     endTime = datetime.datetime.strptime("01/26/20 22:45:00", '%m/%d/%y %H:%M:%S') ):
    '''
    Document string....
    '''


    # essential edit... 
    
    
    
    numTh = detailsDF.shape[0]

    # total minutes from earliest possible Show Time to Latest Possible.  This will be used to form our grid.
    totalMinutes = (endTime-startTime).total_seconds()/60
    # number of time units needed.
    numTU = floor(totalMinutes/TUsize) # flooring keeps everything within bounds.

    # Reading the Bookings file.
    TB = bookingDF
    # no one likes /, -, or spaces in column names. - is a special char.
    TB.columns = TB.columns.str.replace('[/\- ]', '_')

    # Cut the Dataframe to only keep what we are currently using.
    # We will need to come back to this to include more features.
    TB['totalPostTime'] = TB.Runtime + TB.Post_Clean_Time
    TB['totalPreTime'] = TB.Pre_Show_Advertising + TB.Trailers
    TB = TB.drop(columns = ['Playing', 'Format', "Auditorium_Size_Preference", "Expected_Demand",'Pre_Show_Advertising', 'Trailers', 'Post_Clean_Time', "Unnamed:_10", 'Custom_Auditorium', 'Custom_Showtime', "Minimum_Spacing_between_film"])

    # Create model
    model = ConcreteModel()

    # Parameters...
    movies = TB.Print_Film
    theatres = list(range(numTh))
    timeUnits = list(range(numTU))
    # lesser params...
    # Creates a dictionary of the number of time units need to show a movie by movie.
    moviePostTimeUnits = {TB.Print_Film[i]:ceil(TB.totalPostTime[i]/TUsize) for i in range(len(movies))}
    moviePreTimeUnits = {TB.Print_Film[i]:ceil(TB.totalPreTime[i]/TUsize) for i in range(len(movies))}
    movieRunTimes = {TB.Print_Film[i]:TB.Runtime[i] for i in range(len(movies))}


    # I want to index my minimum performance with movies... so... let's make a dictionary.
    movieMinimumPerformanceCount = {TB.Print_Film[i]:TB.Minimum_Performance_Count[i] for i in range(len(movies))}

    # Variable
    model.startTimes = Var(movies, theatres, timeUnits, domain = Binary)
    # model.busyness = Var(theatres, timeUnits, domain = Binary)
    model.minMovieTimeDiff = Var(movies)

    # Objective function
    model.objectiveFun = Objective(
        expr = numTU*100*sum([model.startTimes[m,th,t] for m in movies for th in theatres for t in timeUnits]) + TUsize*sum([model.minMovieTimeDiff[m] for m in movies]),
        sense = maximize)

    # Constraints...
    model.noTwoShows = ConstraintList()
    for th in theatres:
        for t in timeUnits:
            model.noTwoShows.add(sum(
                [
                    model.startTimes[m,th,lil_t] 
                    for m in movies
                    for lil_t in range(max(0,t+1-moviePostTimeUnits[m]), min(numTU,t+ moviePreTimeUnits[m])) 
                ]) <=1)

    model.movieMinimumShows = ConstraintList()
    for m in movies:
        model.movieMinimumShows.add(sum(
            [
                model.startTimes[m,th,t] for th in theatres for t in timeUnits
            ]) >= movieMinimumPerformanceCount[m] )  # this is the dict I created...

    model.ShowSpread = ConstraintList() # A show only starts once in a given interval of time
    # ShowSpread is necessary for the setTheMinMovieTimeDiff to work correctly... it prevents double t and double s distuations.
    for m in movies:
        for t in timeUnits:
            model.ShowSpread.add(sum(
                [
                    model.startTimes[m,th,lil_t] 
                    for th in theatres 
                    for lil_t in range(t, min(numTU,t + ceil(15/TUsize))) # converting 15 minutes to time intervals.
                ]) <= 1 )

    model.setTheMinMovieTimeDiff = ConstraintList()
    for m in movies:
        for s in timeUnits:
            for t in timeUnits:
                        if t > s:
                            model.setTheMinMovieTimeDiff.add(
                                model.minMovieTimeDiff[m] <= t - s + numTU*(2 - sum([model.startTimes[m, th, t] + model.startTimes[m, th, s] for th in theatres]))
                            )
    #                            model.minMovieTimeDiff[m] <= 4*numTU + (-2*numTU + t)model.startTimes[m, th1, t] + (-2*numTU + s)model.startTimes[m, th2, s]

    results = SolverFactory('glpk').solve(model, timelimit = 60*1)
    results.write() # comment out eventually. 

    # extracting the variable from the solved model
    extractedStartTimes = model.startTimes.extract_values()

    # Grabbing the actual start times from the variable and making a usable dataframe.
    cols = ['movie', 'theatre', 'timeUnit']
    startTimesDF = pd.DataFrame(columns = cols)
    for index in extractedStartTimes:
        if extractedStartTimes[index] == 1:
            startTimesDF = startTimesDF.append(pd.DataFrame([list(index)], columns = cols), ignore_index = True)

    # Converting the timeUnits into actual Date/times and adding it to the dataframe.
    startTimesDF['startTimeDate'] = [startTime + datetime.timedelta(seconds =60*tU*TUsize)  for tU in startTimesDF.timeUnit]

    startTimesDF['theatre'] = startTimesDF['theatre']+1
    
    startTimesDF['endTimeDate'] = [startTime + datetime.timedelta(seconds =int(60*row[1].timeUnit*TUsize + 60*movieRunTimes[row[1].movie])) for row in startTimesDF.iterrows()]
    

    
    # [startTime + datetime.timedelta(seconds =60*tU*TUsize + movieRunTimes[startTimesDF.movie]) for tU in startTimesDF.timeUnit]
    
    return startTimesDF

if __name__ == '__main__':
    aSchedule = GenerateSchedule(pd.read_csv( "DataIn/TB_original" + "/Theatre_Bookings.csv"), 
                                 pd.read_csv( "DataIn/TB_original" + "/Theatre_Details.csv"))
    print(aSchedule)
    