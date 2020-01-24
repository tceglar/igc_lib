#!/usr/bin/env python
from __future__ import print_function

import os
import sys
import igc_lib
import lib.dumpers as dumpers
import argparse     as ap
import time
import geojson as gjson


def print_flight_details(flight):
    print("Flight:", flight)
    print("Takeoff:", flight.takeoff_fix)
    thermals = flight.thermals

    for i in range(len(thermals)):
        thermal = thermals[i]
        print("  thermal[%d]:" % i, thermals[i])
    print("Landing:", flight.landing_fix)


def dump_flight(flight, input_file):
    input_base_file = os.path.splitext(input_file)[0]
    wpt_file = "%s-thermals.wpt" % input_base_file
    cup_file = "%s-thermals.cup" % input_base_file
    thermals_csv_file = "%s-thermals.csv" % input_base_file
    flight_csv_file = "%s-flight.csv" % input_base_file
    kml_file = "%s-flight.kml" % input_base_file

    print("Dumping thermals to %s, %s and %s" %
          (wpt_file, cup_file, thermals_csv_file))
    dumpers.dump_thermals_to_wpt_file(flight, wpt_file, True)
    dumpers.dump_thermals_to_cup_file(flight, cup_file)

    print("Dumping flight to %s and %s" % (kml_file, flight_csv_file))
    dumpers.dump_flight_to_csv(flight, flight_csv_file, thermals_csv_file)
    dumpers.dump_flight_to_kml(flight, kml_file)

   
def dump_to_geojson(output_filename, list_thermals):
    """
    
    """
    features = []

    for thermal in list_thermals:
        #print(thermal)
        lat = thermal.enter_fix.lat
        lon = thermal.enter_fix.lon
        vario = round(thermal.vertical_velocity(),2)
        altitude = int(thermal.enter_fix.press_alt)

        json_point=gjson.Point((lon, lat, altitude))
        features.append(gjson.Feature(geometry=json_point, properties={"vario": vario, "altitude": altitude}))

    feature_collection = gjson.FeatureCollection(features)
    #Write output
    with open('{}.geojson'.format(output_filename), 'w') as f:
        gjson.dump(feature_collection, f)

def main():
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
    
    # Read .igc files names in a directory
    files = []
    for file in os.listdir("{}".format(dir)):
        if file.endswith(".igc"):
            files.append(file)


    ### Collect all flights
    global_thermals = []

    ### Analyse files
    for file in files:
        flight = igc_lib.Flight.create_from_file("{0}/{1}".format(dir, file))
        
        if flight.valid:
            print(file)
            #print_flight_details(flight)
            global_thermals.extend(flight.thermals)

    # Dump to GeoJSON
    dump_to_geojson(output, global_thermals)
    print("GeoJson output to: {}".format(output))




if __name__ == "__main__":
    main()
