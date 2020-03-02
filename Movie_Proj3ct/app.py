import dash 
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import pandas as pd
import numpy as np
import datetime
from datetime import timedelta
import plotly.figure_factory as ff
import dash_table
import itertools
import CreateSchedules
import os
import re


#Create the schedules...
CreateSchedules.CheckSchedules()
#extract all the csv file name in schedule folder
Schedules_avail = [ f.name for f in os.scandir('Schedules') if f.is_file() & bool(re.search('.*\.csv$', f.name))]

#Extract the name of the schedule
Schedules_avail = [x.replace('_Schedule.csv', '') for x in Schedules_avail]

#create options for dropdown
schedulesDict = [{'label' : i, 'value': i} for i in Schedules_avail]

app = dash.Dash(__name__)

app.layout = html.Div(
    children = [html.H1('Movie Schedules for I20 cinemas'),
                
                #dropdown
        html.P(children=[
        html.Label('Select a Schedule'),
        dcc.Dropdown(id='select', options= schedulesDict, multi = False, value = "TB_Original")],
            style = {'width':'400px'}),
                
        html.Div(children = [
            html.P("C: Cleaning time, T: Trailer time, P: Pre-show advertisement"),
            dcc.Graph(id = 'gantt'),
            html.P("Type in a movie or time slot to filter your choices:"),
            dash_table.DataTable( id='showtime',
            columns=[{'name' : 'Movie', 'id' : 'movie'},
                     {'name' : 'Theatre', 'id' : 'theatre'},
                     {'name' : 'Start Time', 'id' : 'startTimeDate'}],
            sort_action= "native",
            sort_mode="multi",
            filter_action="native",
            row_selectable="single"),
        html.A('Download Data',
        id='download-link',
        href="",
        target="_blank"
    )
                ]) #closes out div for graph and data table
    ]) #closes out outer div

@app.callback(
        [Output('gantt', 'figure'),
        Output('showtime','data')],
        [Input('select', 'value')])

def update_output(select):
   
    startTimesDF = pd.read_table('Schedules/' + select + '_Schedule.csv', delimiter = ',', header = 'infer')
    startTimesDF = startTimesDF.sort_values(by=['theatre'],ascending=False)
    
   
    #I will generate pre and post show time data, I manually compute/input time unit and duration for each of these actitives here. 
    #generate cleaning data
    #cleaning starts when movie ends
    cleaning_data = startTimesDF[['theatre','endTimeDate']]
    #change the name so later I can concatenate the data
    cleaning_data.columns = ['theatre','startTimeDate']
    #create time unit, make it 0 so this column is not missing for cleaning time
    cleaning_data['timeUnit'] = 0
    #check to see if this block is a movie
    cleaning_data['check'] = 'N'
    #compute endtime for cleanings, which is 15 mins
    cleaning_data['endTimeDate'] = pd.to_datetime(cleaning_data['startTimeDate']) + timedelta(minutes=15)
    #create title for those time slots on Gantt chart
    cleaning_data['movie'] = 'C' 
    

    
    #generate trailer data
    #Trailer ends when movies starts
    trailer_data = startTimesDF[['theatre','startTimeDate']]
    #change the name of columns
    trailer_data.columns = ['theatre','endTimeDate']
    #create time unit, same logic as cleaning time
    trailer_data['timeUnit'] = 0
    trailer_data['check'] = 'N'    #check to see if this block is a movie
    #compute start time for trailer, which is 20 min before the movie starts
    trailer_data['startTimeDate'] = pd.to_datetime(trailer_data['endTimeDate']) - timedelta(minutes=20)
    #create title for those time slots on Gantt chart
    trailer_data['movie'] = 'T' 
    
    #generate preshow_data
    #preshow ends when trailer starts
    preshow_data = trailer_data[['theatre','startTimeDate']]
    #change the name of columns    
    preshow_data.columns = ['theatre','endTimeDate']
    #create time unit same logic as above
    preshow_data['timeUnit'] = 0
    preshow_data['check'] = 'N'    #check to see if this block is a movie

    #compute start time for trailer, which is 30 min before the trailer starts
    preshow_data['startTimeDate'] = pd.to_datetime(preshow_data['endTimeDate']) - timedelta(minutes=30)
    #create title for those time slots on Gantt chart
    preshow_data['movie'] = 'P' 
    
    
    startTimesDF_chart = pd.concat([startTimesDF,cleaning_data, trailer_data,preshow_data])
    
    #check column used to check if the time slot is a movie or not, if not a movie, the annotated time is 5 mins after start time, if it is a movie, then the annotation will be have x axis at 50 mins after the movie starts. I have to do this manually and have not found a way to to position the annotation nicely
        #create columns to position the label
    startTimesDF_chart['AnnotatedTime'] =  np.where(startTimesDF_chart['check'] == 'N', pd.to_datetime(startTimesDF_chart['startTimeDate']) + timedelta(minutes=5), pd.to_datetime(startTimesDF_chart['startTimeDate']) + timedelta(minutes=50))
    

    #copied from LP project, used to create dictionaries for plot
    
    showit = [dict(Task= "Theater" + str(row[1].theatre), Start= row[1].startTimeDate, Finish = row[1].endTimeDate, Resource = row[1].movie) for row in startTimesDF_chart.iterrows()] 
    
    #colors = dict(T = 'red', C = 'blue', P = 'black')
    #unique_movie = np.unique(startTimesDF.movie)
    
    #colors2 = dict((movie, np.random.rand(3,)) for movie in unique_movie)
    #colors = colors.update(colors2), 
    fig = ff.create_gantt(showit, index_col='Resource', group_tasks=True, show_hover_fill = True,show_colorbar=True,showgrid_x=True)    
    
   
    
    #create dictionnary for info for the annotation
    annots = [dict(x=row[1].AnnotatedTime,y=row[1].theatre-1,text=row[1].movie, showarrow=False, font=dict(color='white')) for row in startTimesDF_chart.iterrows() ]
    #[dict(x=row.startTimeDate,y=row.theater,text=row.movie, showarrow=False, font=dict(color='white'))]
  
    fig['layout']['annotations'] = annots
    
    
    return fig, startTimesDF.to_dict('records')


@app.callback(
    Output('download-link', 'href'),
    [Input('select', 'value')])
def update_download_link(select):
    startTimesDF = pd.read_table('Schedules/' + select + '_Schedule.csv', delimiter = ',', header = 'infer')

    csv_string = startTimesDF.to_csv()
    return csv_string




if __name__ == "__main__":
    app.run_server(debug = True)