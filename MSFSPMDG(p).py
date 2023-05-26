import xml.etree.ElementTree as ET
import argparse
import sys
import re
from datetime import datetime


def dms_to_decimal(dms_str):
    direction = dms_str[0]
    dms_str = re.sub(r'[^0-9. ]', '', dms_str[1:])
    degrees, minutes, seconds = [float(part) for part in dms_str.split()]
    decimal_degrees = degrees + minutes / 60 + seconds / 3600
    if direction in ('S', 'W'):
        decimal_degrees *= -1
    return decimal_degrees


def parse_msfs(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    flight_plan = root.find('FlightPlan.FlightPlan')

    waypoints = flight_plan.findall('ATCWaypoint')

    waypoint_data = []

    for i, waypoint in enumerate(waypoints):
        id = waypoint.get('id')

        # Skip SID/STAR/APP waypoints
        if waypoint.find('ATCWaypointType').text == 'SIDSTARAPP':
            continue

        position = waypoint.find('WorldPosition').text
        latitude_dms, longitude_dms, altitude = position.split(',')
        latitude = dms_to_decimal(latitude_dms)
        longitude = dms_to_decimal(longitude_dms)
        altitude = int(float(altitude[1:]))

        # Set type to 1 for airports (departure and arrival) and 5 for other waypoints
        type = 1 if i == 0 or i == len(waypoints) - 1 else 5

        waypoint_data.append({
            'id': id,
            'latitude': latitude,
            'longitude': longitude,
            # Set altitude to 35000 for non-airport waypoints
            'altitude': altitude if type == 1 else 35000,
            'type': type,
            'restriction_phase': 1 if type == 1 else 0,
            'restriction_altitude_type': '-',
            'restriction_altitude': altitude if type == 1 else -1000000,
            'restriction_speed': -1000000
        })

    return waypoint_data


def convert_to_pmdg(waypoints):
    pmdg = []
    pmdg.append(
        f'Generated by MSFSPMDG {datetime.utcnow().strftime("%d %b %Y %H:%M")} UTC')
    pmdg.append('')
    pmdg.append(str(len(waypoints)))
    pmdg.append('')

    for waypoint in waypoints:
        pmdg.append(waypoint['id'])
        pmdg.append(str(waypoint['type']))
        pmdg.append('DIRECT')
        altitude = waypoint['altitude'] if waypoint['type'] == 1 else 35000
        pmdg.append(
            f"1 N {waypoint['latitude']:.4f} W {waypoint['longitude']:.4f} {altitude}")
        pmdg.append('-----')
        pmdg.append('1' if waypoint['type'] == 1 else '0')  # departure
        pmdg.append('0')
        if waypoint['type'] == 1:  # for airports
            pmdg.append('')  # New line
            # restriction phase: 1 for departure, 0 for arrival
            pmdg.append('1' if waypoint['id'] == waypoints[0]['id'] else '0')
            # restriction altitude: use actual altitude for airports
            pmdg.append(str(altitude))
            pmdg.append('-')
            pmdg.append('-1000000')
            pmdg.append('-1000000')
            pmdg.append('')  # New line
        else:  # for non-airport waypoints
            pmdg.append('0')
            pmdg.append('')  # New line
    return "\n".join(pmdg)


def main():
    parser = argparse.ArgumentParser(
        description='Convert MSFS flight plan to PMDG .rte flight plan.')
    parser.add_argument('input', help='Input MSFS flight plan (.pln)')
    parser.add_argument('output', help='Output PMDG flight plan (.rte)')

    args = parser.parse_args()

    waypoints = parse_msfs(args.input)
    pmdg_plan = convert_to_pmdg(waypoints)

    with open(args.output, 'w') as f:
        f.write(pmdg_plan)

    print(f'Converted {args.input} to {args.output}')


if __name__ == '__main__':
    main()
