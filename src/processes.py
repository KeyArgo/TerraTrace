"""
processes.py

High-level operations and workflows that orchestrate the use of functions 
from other modules. Includes the overall process of converting JSON formatted 
data to KML.
"""

import json
import os
import logging
import geojson
from datetime import datetime
from geopy.distance import distance as geopy_distance
from geopy.point import Point
from geographiclib.geodesic import Geodesic

# Import statements (keep these as they were in your original file)
from computation import gather_monument_data, gather_polygon_points, compute_point_based_on_method
from file_io import save_kml_to_file, generate_kml_placemark, generate_complete_kml, generate_kml_polygon, setup_directories
from io_operations import (get_coordinate_format_only, ask_use_same_format_for_all, polygon_main_menu, 
                           get_num_points_to_compute, tie_point_menu, get_export_decision, 
                           get_file_type_choice, gather_tie_point_coordinates, get_no_tie_point_coordinates)
from data_operations import initialize_data, check_polygon_closure, finalize_json_structure, finalize_data, is_polygon_close_to_being_closed
from display_operations import display_computed_point, display_starting_point, display_monument_point

# Setup logging
log_directory = "../logs"
if not os.path.exists(log_directory):
    os.makedirs(log_directory)
logging.basicConfig(level=logging.DEBUG, filename='../logs/application.log', filemode='a', 
                    format='%(asctime)s:%(levelname)s:%(message)s')


def create_kml_content(data, polygon_name="GPS Polygon and Reference Point"):
    """
    Creates KML content for a polygon and an optional monument placemark.

    This function generates KML content based on the provided polygon data. It includes
    logic to close the polygon properly and to add a monument placemark if provided.

    Args:
        data (dict): The data containing polygon points and, optionally, a monument.
        polygon_name (str): The name to be given to the polygon in the KML file.

    Returns:
        str: The complete KML content as a string, or None if an error occurs or data is not available.
    """
    try:
        # Initiating KML content generation
        if not data.get('polygon'):
            print("No polygon data available to create KML content.")
            return None
        # Explanation: Verifies the presence of polygon data. If not available, exits the function.

        # Process monument data if available
        monument_kml = ""
        polygon_kml = ""
        # Explanation: Initializes variables for storing KML content of the monument and polygon.

        # Generating placemark KML for the monument, if available
        monument = data.get('monument', {})
        if monument.get('lat') is not None and monument.get('lon') is not None:
            monument_kml = generate_kml_placemark(monument['lat'], monument['lon'], name=monument.get('label', "Monument"))
            # Explanation: If monument data is present, generates KML for the monument placemark.

        # Prepare polygon points and check if the polygon needs to be closed
        polygon_points = [(point['lat'], point['lon']) for point in data['polygon'] if 'lat' in point and 'lon' in point]
        # Explanation: Extracts latitude and longitude points from the polygon data.

        # Check the distance between the last point and the first point
        if polygon_points:
            start_point = polygon_points[0]
            end_point = polygon_points[-1]
            distance = geopy_distance(start_point, end_point).feet
            # Explanation: Calculates the distance between the first and last points of the polygon.

            # Replace last point with first point if within 10 feet, otherwise append the first point
            if distance <= 10:
                polygon_points[-1] = start_point
            else:
                polygon_points.append(start_point)
            # Explanation: Closes the polygon by ensuring the last point is close enough to the first point.

        polygon_kml = generate_kml_polygon(polygon_points, polygon_name=polygon_name)

        # Combine monument and polygon KML
        complete_kml = generate_complete_kml(monument_kml, polygon_kml, polygon_name) if monument_kml else polygon_kml
        # Explanation: Combines the monument placemark KML and polygon KML into one complete KML string.
        return complete_kml
    except Exception as e:
        print(f"An error occurred while creating KML content: {e}")
        return None


def export_kml(data, kml_content, kml_file_path, polygon_name, points):
    """
    Exports KML content to a specified file path.

    This function handles the creation of KML content based on the provided data and polygon name,
    and then saves the content to a given file path.

    Args:
        data (dict): The data containing polygon points and other relevant information.
        kml_content (str): Pre-generated KML content, if any.
        kml_file_path (str): The file path where the KML file should be saved.
        polygon_name (str): The name to be given to the polygon in the KML file.
        points (list): List of points used in the polygon.

    """
    # Ensuring the polygon is properly closed before exporting
    close_polygon = check_polygon_closure(data)  # Updated function call
    # Explanation: Checks if the polygon is properly closed and updates it if necessary.

    # Generating KML content for the polygon
    kml_content = create_kml_content(data, polygon_name=polygon_name)
    # Explanation: Generates KML content for the polygon using the provided data and polygon name.

    # Verifying file path and KML content
    print("KML File Path in export_kml:", kml_file_path)  # Print for verification
    print("KML Content in export_kml:", kml_content[:100])  # Print first 100 characters for verification
    # Explanation: Outputs the KML file path and a snippet of the KML content for verification purposes.

    # Save the KML content to the file
    if kml_content:
        save_kml_to_file(kml_content, kml_file_path)
    # Explanation: Saves the generated KML content to the specified file path.

    else:
        print("Failed to generate KML content.")


def export_json(data, json_path, tie_point_used, polygon_name):
    """
    Exports polygon data to a JSON file at a specified path.

    Handles the preparation of data for JSON export, ensures the directory exists for the file,
    and manages exceptions during the file save process.

    Args:
        data (dict): The polygon data to be exported.
        json_path (str): The file path where the JSON file will be saved.
        tie_point_used (bool): Indicates whether a tie point was used in creating the polygon.
        polygon_name (str): The name of the polygon.

    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        # Explanation: Creates the directory for the JSON file if it doesn't already exist.

        # Prepare data for JSON export
        final_data = finalize_json_structure(data, tie_point_used, polygon_name)  # Include polygon_name
        # Explanation: Prepares and structures the polygon data for JSON export.

        # Attempt to save the JSON file
        with open(json_path, 'w') as file:
            json.dump(final_data, file, indent=4)
        # Explanation: Writes the structured data to the JSON file with indentation for readability.

        # Error handling
        logging.info(f"JSON file saved successfully at {json_path}")
        print(f"JSON file saved successfully at {json_path}")

    except json.JSONDecodeError as json_err:
        logging.error(f"JSON encoding error: {json_err}")
        print(f"JSON encoding error: {json_err}")

    except IOError as io_err:
        logging.error(f"IO error while saving JSON file: {io_err}")
        print(f"IO error while saving JSON file: {io_err}")

    except Exception as e:
        logging.error(f"Unexpected error occurred while saving JSON file: {e}")
        print(f"Unexpected error occurred while saving JSON file: {e}")


def create_kml_process(polygon_name):
    data, tie_point_used = gather_data_from_user(polygon_name)
    if not data or 'polygon' not in data:
        print("Data gathering was not completed. Exiting.")
        return None

    points = [(point['lat'], point['lon']) for point in data['polygon']]
    print("Polygon Points:", points)

    kml_content = create_kml_content(data, polygon_name)
    
    if not check_polygon_closure(data):
        print("Warning: Your polygon is not closed. Automatically closing the polygon.")
        closing_point = data['polygon'][0].copy()
        data['polygon'].append(closing_point)
        closing_point_id = closing_point.get('id', 'P1')
        if 'construction_sequence' in data and data['construction_sequence'][-1] != closing_point_id:
            data['construction_sequence'].append(closing_point_id)

    if get_export_decision():
        file_type_choice = get_file_type_choice().upper()  # Convert to uppercase
        kml_directory, json_directory = setup_directories()

        default_filename = polygon_name.replace(" ", "_")
        filename = input(f"Enter the filename for the file (without extension) [{default_filename}]: ") or default_filename
        kml_path = os.path.join(kml_directory, f"{filename}.kml")
        json_path = os.path.join(json_directory, f"{filename}.json")
        geojson_path = os.path.join(json_directory, f"{filename}.geojson")  # Add GeoJSON path

        while os.path.exists(kml_path) or os.path.exists(json_path) or os.path.exists(geojson_path):
            print("A file with that name already exists. Please choose a different filename.")
            filename = input(f"Enter a new filename for the file (without extension) [{default_filename}]: ") or default_filename
            kml_path = os.path.join(kml_directory, f"{filename}.kml")
            json_path = os.path.join(json_directory, f"{filename}.json")
            geojson_path = os.path.join(json_directory, f"{filename}.geojson")  # Update GeoJSON path

        logging.debug("Data before exporting: %s", data)

        if file_type_choice in ["K", "A"]:
            try:
                export_kml(data, kml_content, kml_path, polygon_name, points)
                logging.info("KML file exported successfully: %s", kml_path)
                print(f"KML file exported successfully: {kml_path}")
            except Exception as e:
                logging.error("Failed to export KML file: %s", e)
                print(f"Failed to export KML file: {e}")

        if file_type_choice in ["D", "A"]:
            try:
                export_json(data, json_path, tie_point_used, polygon_name)
                print(f"JSON file exported successfully: {json_path}")
            except Exception as e:
                logging.error("Failed to export JSON file: %s", e)
                print(f"Failed to export JSON file: {e}")

        if file_type_choice in ["G", "A"]:  # Add GeoJSON option
            try:
                geojson_path = os.path.join(json_directory, f"{filename}.geojson")
                save_as_geojson(data, geojson_path)
                print(f"GeoJSON file exported successfully: {geojson_path}")
            except Exception as e:
                logging.error("Failed to export GeoJSON file: %s", e)
                print(f"Failed to export GeoJSON file: {e}")

        if file_type_choice == 'A':
            print("KML, JSON, and GeoJSON files have been saved.")
        elif file_type_choice == 'K':
            print("KML file has been saved.")
        elif file_type_choice == 'D':
            print("JSON file has been saved.")
        elif file_type_choice == 'G':
            print("GeoJSON file has been saved.")
    else:
        print("Export cancelled by the user.")

    return data


def main_choice_2_process(data):
    """
    Handles a specific process flow involving logging setup and various operations.

    Starts by setting up a unique log file for the session, then progresses through
    operations like getting the initial polygon point and setting the coordinate format.

    Args:
        data: The data to be processed (description of data structure/type needed).

    Returns:
        A tuple containing processed data, list of points, user choice, and coordinate format.
    """
    # Set up logging directory and create a unique log file for the session
    log_directory = "../logs"
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    log_filename = os.path.join(log_directory, f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

    logging.basicConfig(filename=log_filename, level=logging.INFO,
                        format='%(asctime)s:%(levelname)s:%(message)s')

    choice = None  # Initialize choice variable

    # Get initial polygon point and validate its existence
    lat, lon = get_initial_polygon_point()  # Retrieves the first point of the polygon from user input or file
    if lat is None or lon is None:
        logging.error("Initial polygon point is None.")
        return None, [], choice, None  # Return early if initial point is not provided

    logging.info(f"Initial point set at Latitude: {lat}, Longitude: {lon}")

    # Get the format for the coordinates from the user
    coordinate_format = get_coordinate_format_only()  # Ask user for the format of latitude and longitude values
    if coordinate_format is None:
        logging.error("Coordinate format is None.")
        return None, [], choice, None  # Return early if coordinate format is not specified

    use_same_format_for_all = ask_use_same_format_for_all()  # Query if the same coordinate format should be used for all points

    # Initialize a list with the initial point
    points = [{'lat': lat, 'lon': lon}]
    # Display the computed initial point
    display_computed_point(points, lat, lon, is_initial_point=True)  # Display the initial point for user confirmation

    # Get the number of additional points to compute
    num_points = get_num_points_to_compute()  # Ask user for the number of additional points to include in the polygon
    if num_points is None:
        # Log a warning if the number of points is not specified and terminate the function
        logging.warning("Number of points to compute is None.")
        return None, [], choice, coordinate_format  # Include coordinate_format in the return statement

    try:
        # Attempt to gather new points for the polygon, handling any exceptions
        data, new_points, new_choice = gather_polygon_points(
            data, coordinate_format, lat, lon, use_same_format_for_all, num_points
        )
    except ValueError as e:
        # Log an error if an exception occurs in gather_polygon_points
        logging.error(f"Error in gather_polygon_points: {e}")
        return None, [], choice, coordinate_format  # Return with default values in case of error

    # Add the newly gathered points to the points list
    points.extend(new_points)
    # Update the choice if a new choice is provided
    if new_choice is not None:
        choice = new_choice

    # Prepare points for checking if the polygon is closed
    prepared_points = prepare_points_for_distance_check(points)
    if not prepared_points:
        # Log an error if no points are prepared for distance check
        logging.error("No prepared points available. Cannot check if the polygon is closed.")
        return data, points, choice, coordinate_format

    # Close the polygon if the last point does not match the first point
    if not prepared_points[-1] == prepared_points[0]:
        logging.info("The polygon is not closed. Adjusting the last point to close the polygon.")
        closing_point = data['polygon'][0].copy()  # Duplicate the first point to use as the closing point
        closing_point['id'] = 'P1'  # Assign an ID to the closing point
        data['polygon'].append(closing_point)  # Add the closing point to the polygon

    # Return the updated data, points list, user choice, and coordinate format
    return data, points, choice, coordinate_format  # Return all four values


def ensure_directories_exist():
    """
    Ensures that the necessary directories for saving JSON and GeoJSON files exist.
    If they do not exist, they are created automatically.
    """
    directories = ["saves/json", "saves/geojson"]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Directory created: {directory}")
            

def gather_data_from_user(polygon_name):
    ensure_directories_exist()

    data = initialize_data()
    log_data = {
        "polygon_name": polygon_name,
        "coordinate_format": "",
        "tie_point": {},
        "polygon_points": [],
        "metadata": {
            "user": "UserName",
            "date_created": datetime.now().isoformat()
        }
    }
    
    tie_point_used = False
    use_same_format_for_all = False
    main_choice = polygon_main_menu()
    choice = None

    if main_choice == "1":
        tie_point_used = True
        lat, lon = gather_tie_point_coordinates()
        if lat is None and lon is None:
            print("Exiting to main menu.")
            return None, tie_point_used

        data.setdefault("tie_point", {}).update({"lat": lat, "lon": lon})
        log_data["tie_point"] = {"latitude": lat, "longitude": lon}
        log_data["coordinate_format"] = get_coordinate_format_only()
        display_starting_point(lat, lon)
        use_same_format_for_all = ask_use_same_format_for_all()
        point_use_choice = tie_point_menu()

        if point_use_choice == "1":
            coordinate_format, results = gather_monument_data(log_data["coordinate_format"], lat, lon, use_same_format_for_all)
            if results:
                lat, lon, monument_label, bearing, distance = results
                data["monument"] = {"lat": lat, "lon": lon, "label": monument_label, "bearing_from_prev": bearing, "distance_from_prev": distance}
                log_data["polygon_points"].append({
                    "id": monument_label,
                    "bearing": bearing,
                    "distance_feet": distance,
                    "computed_coordinates": {"lat": lat, "lon": lon}
                })
                display_monument_point(lat, lon)
                num_points = get_num_points_to_compute()
                data, new_choice = transition_to_polygon_points(data, coordinate_format, lat, lon, use_same_format_for_all, num_points, log_data)
                if new_choice is not None:
                    choice = new_choice
            else:
                print("Monument data could not be gathered. Exiting to main menu.")
                return None, tie_point_used
        elif point_use_choice == "2":
            num_points = get_num_points_to_compute()
            data, new_choice = transition_to_polygon_points(data, log_data["coordinate_format"], lat, lon, use_same_format_for_all, num_points, log_data)
            if new_choice is not None:
                choice = new_choice

    elif main_choice == "2":
        lat, lon = get_initial_polygon_point()
        if lat is None or lon is None:
            print("Exiting to main menu.")
            return None, tie_point_used
        
        log_data["coordinate_format"] = get_coordinate_format_only()
        num_points = get_num_points_to_compute()
        data, new_choice = transition_to_polygon_points(data, log_data["coordinate_format"], lat, lon, use_same_format_for_all, num_points, log_data)
        if new_choice is not None:
            choice = new_choice

    if 'polygon' in data and data['polygon']:
        data = finalize_data(data, use_same_format_for_all, log_data["coordinate_format"], choice)
    else:
        print("No polygon points were added. Exiting to main menu.")
        return None, tie_point_used

    # Save to JSON
    filename = f"{log_data['polygon_name'].replace(' ', '_')}"
    json_path = f"saves/json/{filename}.json"
    with open(json_path, "w") as json_file:
        json.dump(log_data, json_file, indent=4)
    print(f"JSON file saved successfully at {json_path}")

    # Save to GeoJSON
    geojson_path = f"saves/geojson/{filename}.geojson"
    save_as_geojson(log_data, geojson_path)
    print(f"GeoJSON file saved successfully at {geojson_path}")

    return data, tie_point_used
    

def get_initial_polygon_point():
    """
    Prompt user to enter the initial point of a polygon.

    This function facilitates the entry of the first polygon point when a tie point is not used.
    It handles coordinate format choice and coordinate entry through a helper function.

    Returns:
        tuple: A tuple containing the latitude and longitude of the initial point, 
               or (None, None) if the user chooses to exit.
    """
    print("\nEntering `get_initial_polygon_point` function.")
    print("\n--------------- Initial Polygon Point Entry ---------------")
    print("Please enter the initial point of your polygon.")
    
    lat, lon = get_no_tie_point_coordinates()
    
    if lat is None or lon is None:
        print("Exiting. No complete coordinates provided.")
        return None, None

    return lat, lon


def polygon_closure_for_no_tie_point_export(data):
    """
    Adjusts the last point of a polygon to ensure closure when no tie point is used.

    This function checks if the polygon formed by the points in the data dictionary is close enough
    to being closed. If so, it adjusts the last point to match the first point, effectively closing the polygon.

    Args:
        data (dict): A dictionary containing polygon data.

    Returns:
        dict: The updated data dictionary with the adjusted polygon for closure.
    """
    # Retrieve the list of polygon points from the data dictionary
    points_dicts = data.get('polygon', [])  # Retrieve the list of polygon points from the data dictionary
    points = prepare_points_for_distance_check(points_dicts)  # Convert points into a format suitable for distance checking

    # If the polygon is almost closed, adjust the last point to close it
    if is_polygon_close_to_being_closed(points):
        print("The polygon is close enough to being closed. Adjusting the last point to the initial point.")
        data['polygon'][-1]['id'] = data['polygon'][0]['id']  # Align the last point with the first to close the polygon
        data['polygon'][-1]['lat'] = data['polygon'][0]['lat']
        data['polygon'][-1]['lon'] = data['polygon'][0]['lon']
        if 'construction_sequence' in data:
            data['construction_sequence'][-1] = data['construction_sequence'][0]  # Update the construction sequence to reflect this closure

    return data


def prepare_points_for_distance_check(points):
    """
    Converts a list of point representations into a uniform format for distance calculations.

    This function processes a list of points, which can be either dictionaries with 'lat' and 'lon' keys,
    or tuples, and converts them into a list of (lat, lon) tuples. This uniform format is required for
    subsequent distance checking operations.

    Args:
        points (list): A list of points in various formats.

    Returns:
        list: A list of (lat, lon) tuples, or an empty list if an error occurs.
    """
    prepared_points = []
    for point in points:
        if isinstance(point, dict):
            try:
                prepared_point = (float(point['lat']), float(point['lon']))  # Convert dictionary entries to a (lat, lon) tuple
            except (KeyError, TypeError, ValueError) as e:
                logging.error(f"Error: Invalid point dictionary detected: {point} - {e}")
                return []  # Return empty list if conversion fails
        elif isinstance(point, (list, tuple)):  # Convert list or tuple entries to a tuple of floats
            try:
                prepared_point = tuple(map(float, point))
            except ValueError as e:
                logging.error(f"Error: Invalid point list/tuple detected: {point} - {e}")
                return []  # Return empty list if conversion fails
        else:
            # Log an error for unrecognized point formats and return an empty list
            logging.error(f"Error: Point data is in an unrecognized format: {point}")
            return []  # Return empty list for unrecognized point formats
        prepared_points.append(prepared_point)
    return prepared_points


def transition_to_polygon_points(data, coordinate_format, lat, lon, use_same_format_for_all, num_points, log_data):
    from io_operations import get_bearing_and_distance

    for i in range(num_points):
        if not use_same_format_for_all:
            coordinate_format = get_coordinate_format_only()
        
        bearing, distance = get_bearing_and_distance(coordinate_format)
        if bearing is None and distance is None:
            break
        
        new_lat, new_lon = compute_new_coordinates(lat, lon, bearing, distance)
        
        point_data = {
            "id": f"P{len(data.get('polygon', [])) + 1}",
            "bearing": bearing,
            "distance_feet": distance,
            "lat": new_lat,  # Add this line
            "lon": new_lon,  # Add this line
            "computed_coordinates": {"lat": new_lat, "lon": new_lon}
        }
        
        data.setdefault('polygon', []).append(point_data)
        log_data["polygon_points"].append(point_data)
        
        display_computed_point(data['polygon'], new_lat, new_lon)
        
        lat, lon = new_lat, new_lon

    return data, None

def compute_new_coordinates(lat, lon, bearing, distance):
    # Convert distance from feet to meters
    distance_meters = distance * 0.3048
    
    # Use Geodesic calculations for high precision
    geod = Geodesic.WGS84
    result = geod.Direct(lat, lon, bearing, distance_meters)
    
    return result['lat2'], result['lon2']

def ensure_directories_exist():
    directories = ["saves/json", "saves/geojson"]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"Directory created: {directory}")

def save_as_geojson(log_data, geojson_path):
    features = []
    coordinates = []

    for point in log_data["polygon_points"]:
        coordinates.append([point["computed_coordinates"]["lon"], point["computed_coordinates"]["lat"]])

    geojson_feature = geojson.Feature(
        geometry=geojson.Polygon([coordinates]),
        properties={
            "name": log_data["polygon_name"],
            "format": log_data["coordinate_format"],
            "tie_point": log_data["tie_point"],
            "points": log_data["polygon_points"]  # Include all point data
        }
    )
    geojson_data = geojson.FeatureCollection([geojson_feature])

    with open(geojson_path, "w") as geojson_file:
        geojson.dump(geojson_data, geojson_file, indent=4)
        
def generate_metes_and_bounds(log_data):
    description = f"Beginning at the {log_data['polygon_points'][0]['id']}, "
    for point in log_data['polygon_points'][1:]:
        description += f"thence {point['bearing']} {point['distance_feet']} feet to {point['id']}, "
    description += f"thence to the point of beginning."
    return description

def update_kml_generation(log_data):
    # Implement logic to include detailed point information in KML
    # This might involve modifying your existing KML generation functions
    pass