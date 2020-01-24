# icg2geojson.py
# Author: Tilen Ceglar
# Contributor: Ludovic Lauyner
# January 2020

import os
import datetime
import argparse     as ap
import numpy as np
import geojson as gjson
import time
# from scipy.interpolate import *

DT = 60 # Time averaging factor

# IGC Data extracted out of a .igc file
class IgcData:
    def __init__(self):
        self.b_records = []
        self.records_timestamp = []
        self.records_latitude = []
        self.records_longitude = []
        self.records_pressure_altitude = []
        self.records_engine_noise_level = []

def read_igc(input):
    """reads .igc file and returns in order:
            - gps fix line data
            - epoch timestamps
            - latitudes
            - longitudes
            - pressure altitudes
            - task points
            - raw_data
    """
    raw_data = []
    
    # ENL if applicable
    is_enl_present = False
    enl_index_start = None
    enl_index_stop = None
    
    igcData = IgcData()

    for line in open(input):
        if line.startswith(('HFDTE')):
            day, month, year = line[5:7], line[7:9], line[9:11]
        if line.startswith('I') and line.find("ENL")>-1:                   # Look for ENL location in B message if applicable
            enl_index = line.index("ENL")
            is_enl_present = True
            enl_index_start = int(line[enl_index-4:enl_index-2])
            enl_index_stop = int(line[enl_index-2:enl_index])
        if line.startswith(('B')):
            raw_data.append(line.replace('\n',''))
            HHMMSS, DDMMMMMN, DDDMMMMME, PPPPP = int(line[1:7]), int(line[7:14]), int(line[15:23]), float(line[25:30])

            t_h = float(line[1:3])
            t_m = float(line[3:5])
            t_s = float(line[5:7])
            # time_= (t_h*60+t_m)*60+t_s
            time_as_string = '{0}-{1}-20{2} {3}:{4}:{5}'.format(day,month,year,int(t_h),int(t_m),int(t_s))

            epoch = int(datetime.datetime(2000+int(year), int(month), int(day), int(t_h), int(t_m), int(t_s)).timestamp())

            enl = int(line[enl_index_start:enl_index_stop+1]) if is_enl_present else None

            # Add point into dataset
            is_point_valid = True 
            if not (enl is None) and (enl >= 60 or enl==0):   # Check for ENL level
                is_point_valid = False

            p=1
            g=1
            if line[14]=='S':
                p=-1
            if line[23]=='W':
                g=-1
            lat_ = (float(line[7:9])+(float(line[9:11])+ float(line[11:14])/1000)/60)*p
            lon_ = (float(line[15:18])+(float(line[18:20])+ float(line[20:23])/1000)/60)*g
            pressure_altitude_ = PPPPP

            if is_point_valid:
                igcData.records_timestamp.append(epoch)
                igcData.records_latitude.append(lat_)
                igcData.records_longitude.append(lon_)
                igcData.records_pressure_altitude.append(pressure_altitude_)
                igcData.b_records.append([time_as_string, lat_, lon_, pressure_altitude_])
                igcData.records_engine_noise_level.append(enl)

    return igcData

def average_t(x,dx):
    """time averaging over DT"""
    y = np.mean(np.asarray(x[:(len(x)//dx)*dx]).reshape(-1,dx), axis=1)
    return y

#Grabs directory and outname
parser = ap.ArgumentParser()
parser.add_argument('dir',          help='Path to bulk .igc files'  )
parser.add_argument('output',       help='Geojson file name'        )
arguments = parser.parse_args()

dir = arguments.dir
output = arguments.output

# Create output file name by adding date and time as a suffix
output = arguments.output
now = epoch_time = int(time.time())
dir_name = os.path.dirname(output)
file_name = os.path.basename(output)
output = dir_name + "\\" + str(now) + "_" + file_name

#Read .igc files names in a directory
files = []
for file in os.listdir("{}".format(dir)):
    if file.endswith(".igc"):
        files.append(file)

### Browse through files to collect and compute data
aggregated_points = []
aggregated_varios = []

#Collect all flights and average them over DT
for file in files:
    igc_records = read_igc("{0}/{1}".format(dir, file))

    timestamp_average = average_t(igc_records.records_timestamp,DT)
    latitude_a = average_t(igc_records.records_latitude,DT)
    longitude_a = average_t(igc_records.records_longitude,DT)
    engine_noise_levels =  average_t(igc_records.records_engine_noise_level, DT)

    # Compute average vario
    altitude_average = average_t(igc_records.records_pressure_altitude,DT)
    try:
        vario_average = np.gradient(altitude_average,timestamp_average)
    except:
        # TODO: No idea why the above function fails in some cases...will have to investigate...
        pass

    for timestamp, vario, lat, lon, alt, enl in zip(timestamp_average,vario_average,latitude_a,longitude_a,altitude_average, engine_noise_levels):
        if vario>=0:
            fix = np.stack((int(timestamp), lat,lon,int(alt), int(enl)))
            aggregated_points.append(fix)
            aggregated_varios.append(vario)

### Output: Create gjson points
features = []
for point, m in zip(aggregated_points,aggregated_varios):
    json_point=gjson.Point((point[2],point[1],int(point[3])))
    timestamp = point[0]
    altitude = point[3]
    enl = point[4]
    features.append(gjson.Feature(geometry=json_point, properties={"vario": round(m,2), "altitude": altitude, "enl": enl, "time": timestamp}))

feature_collection = gjson.FeatureCollection(features)

#Write output
with open('{}.geojson'.format(output), 'w') as f:
    gjson.dump(feature_collection, f)
