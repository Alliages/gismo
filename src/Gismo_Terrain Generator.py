# terrain generator
#
# Gismo is a plugin for GIS Environmental Analysis (GPL) started by Djordje Spasic.
# 
# This file is part of Gismo.
# 
# Copyright (c) 2017, Djordje Spasic <djordjedspasic@gmail.com>
# with assistance of Dr. Bojan Savric <savricb@geo.oregonstate.edu>
# Gismo is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#
# Gismo is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with this program. If not, see http://www.gnu.org/licenses/.
#
# The GPL-3.0+ license <http://spdx.org/licenses/GPL-3.0+>

"""
Use this component to create a geometry of the terrain surrounding the chosen location.
Terrain will be created with SRTM 1 arc-second (20 to 30 meters depending on the latitude) grid precision.
-
Component requires that you are connected to the Internet, as it has to download the topography data.
It also requires MapWinGIS application to be installed.
Download and install either 32 bit or 64 bit (depending on your Rhino 5 version) version of MapWinGIS from here:
https://github.com/MapWindow/MapWinGIS/releases
-
Component mainly based on:

"Mathematical cartography", V. Jovanovic, VGI 1983.
"Vincenty solutions of geodesics on the ellipsoid" article by Chris Veness
https://books.google.rs/books/about/Matemati%C4%8Dka_kartografija.html?id=GcXEMgEACAAJ&redir_esc=y
http://www.movable-type.co.uk/scripts/latlong-vincenty.html
-
Provided by Gismo 0.0.1
    
    input:
        _location: The output from the "importEPW" or "constructLocation" component.  This is essentially a list of text summarizing a location on the Earth.
                   -
                   "timeZone" and "elevation" data from the location, are not important for the creation of a terrain.
        radius_: Horizontal distance to which the surrounding terrain will be taken into account.
                 -
                 It can not be shorter than 20 meters or longer than 100 000 meters.
                 -
                 The component itself might inform the user to alter the initial radius_ inputted by the user.
                 This is due to restriction of topography data, being limited to 56 latitude South to 60 latitude North range. If radius_ value for chosen location gets any closer to the mentioned range, the component will inform the user to shrink it for a certain amount, so that the radius_ stops at the range limit.
                 -
                 If not supplied, default value of 100 meters will be used.
                 -
                 In meters.
        north_: Input a vector to be used as a true North direction, or a number between 0 and 360 that represents the clockwise degrees off from the Y-axis.
                -
                If not supplied, default North direction will be set to the Y-axis (0 degrees).
        type_: There are four terrain types:
               -
               0 - terrain will be created as a mesh with rectangular edges
               1 - terrain will be created as a mesh with circular edges
               2 - terrain will be created as a surface with rectangular edges
               3 - terrain will be created as a surface with circular edges
               -
               If nothing supplied, 1 will be used as a default (terrain will be created as a mesh with circular edges).
        origin_: Origin for the final "terrain" output.
                 -
                 If not supplied, default point of (0,0,0) will be used.
        standThickness_: Thickness of the stand.
                         A stand is a basically a base constructed below the terrain mesh/surface. It can be used to create a terrain for cfd analysis or visualization purposes.
                         -
                         If not supplied, default value of 0 (no stand will be created) will be used.
                         -
                         In Rhino document units.
        numOfContours_: Number of elevation contours.
                        If you would not like the elevationContours output to be calculated, set the numOfContours_ input to 0.
                        -
                        If not supplied, default value of 10 elevation contours will be used.
        legendBakePar_: In case your type_ input is set to 0 or 1, you can use the legendBakePar_ input to control the colors with which the final "terrain" mesh will be colored with based on elevation.
                        Use Gismo "Legend Bake Parameters" component's "customColors_" input to control these colors.
                        Also use its fontName_ and fontSize_ inputs to change the font, size of the "title" output.
        bakeIt_: Set to "True" to bake the terrain geometry into the Rhino scene.
                 -
                 If not supplied default value "False" will be used.
        _runIt: !!! ATTENTION !!!   This component may crash Rhino 5 application if radius_ input is set to a value of tens of thousands of meters! This may happen due to Rhino's inability to create such large terrains.
                To prevent this, it is suggested to own a 64 bit version of Rhino 5 and have strong enough PC configuration. If you do not have either of these two, it is recommended to save your .gh definition before running this component!
    
    output:
        readMe!: ...
        terrain: The geometry of the terrain.
                 -
                 Depening on the type_ input it will be either a mesh (type_ = 0 and 1) or a surface (type_ = 2 and 3)
        origin: The origin (center) point of the "terrain" geometry. It's the same as "origin_" input point.
                -
                Use grasshopper's "Point" parameter to visualize it.
                -
                Use this point to move the "terrain" geometry around in the Rhino scene with grasshopper's "Move" component.
        elevation: Elevation of the origin_ input.
                   -
                   In Rhino document units.
        elevationContours: Elevation contours.
                           Their number is defined by the numOfContours_ input. Set the numOfContours_ input to 0, if you would not like the elevationContours to be created.
        title: Title geometry with information about location, radius, north angle.
"""

ghenv.Component.Name = "Gismo_Terrain Generator"
ghenv.Component.NickName = "TerrainGenerator"
ghenv.Component.Message = "VER 0.0.1\nJAN_29_2017"
ghenv.Component.IconDisplayMode = ghenv.Component.IconDisplayMode.application
ghenv.Component.Category = "Gismo"
ghenv.Component.SubCategory = "2 | Terrain"
#compatibleGismoVersion = VER 0.0.1\nJAN_29_2017
try: ghenv.Component.AdditionalHelpFromDocStrings = "1"
except: pass

import Grasshopper.Kernel as gh
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Grasshopper
import datetime
import System
import urllib
import Rhino
import time
import math
import clr
import os
import gc


def checkInputData(maxVisibilityRadiusM, gridSize, source, _type, origin, north, standThickness, numOfContours, downloadTSVLink):
    
    # check if MapWinGIS is properly installed
    gismoGismoComponentNotRan = False  # initial value
    if sc.sticky.has_key("gismo_mapwingisFolder"):
        mapFolder_ = sc.sticky["gismo_mapwingisFolder"]
        iteropMapWinGIS_dll_folderPath, gdalDataPath_folderPath, validInputData, printMsg = gismo_mainComponent.mapWinGIS(mapFolder_)
        if not validInputData:
            maxVisibilityRadiusM = gridSize = source = sourceLabel = _type = typeLabel = origin = northRad = northDeg = standThickness = numOfContours = workingSubFolderPath = downloadTSVLink = unitConversionFactor = unitConversionFactor2 = None
            return maxVisibilityRadiusM, gridSize, source, sourceLabel, _type, typeLabel, origin, northRad, northDeg, standThickness, numOfContours, workingSubFolderPath, downloadTSVLink, unitConversionFactor, unitConversionFactor2, validInputData, printMsg
        if sc.sticky.has_key("MapWinGIS"):
            global MapWinGIS
            import MapWinGIS
        else:
            gismoGismoComponentNotRan = True
    else:
        gismoGismoComponentNotRan = True
    
    if (gismoGismoComponentNotRan == True):
        maxVisibilityRadiusM = gridSize = source = sourceLabel = _type = typeLabel = origin = northRad = northDeg = standThickness = numOfContours = workingSubFolderPath = downloadTSVLink = unitConversionFactor = unitConversionFactor2 = None
        validInputData = False
        printMsg = "The \"Gismo Gismo\" component has not been run. Run it before running this component."
        return maxVisibilityRadiusM, gridSize, source, sourceLabel, _type, typeLabel, origin, northRad, northDeg, standThickness, numOfContours, workingSubFolderPath, downloadTSVLink, unitConversionFactor, unitConversionFactor2, validInputData, printMsg
    
    
    # check inputs
    sourceLabel = "OpenTopography"
    
    if (_type == None):  # "type" is a reserved python word. Use "_type" instead
        _type = 1  # default
        typeLabel = "mesh-circular"  # default
    if (_type == 0):
        typeLabel = "mesh-rectangular"
    elif (_type == 1):
        typeLabel = "mesh-circular"
    elif (_type == 2):
        typeLabel = "surface-rectangular"
    elif (_type == 3):
        typeLabel = "surface-circular"
    elif (_type < 0) or (_type > 3):
        _type = 0
        typeLabel = "mesh-rectangular"
        print "type_ input only supports values 0 to 3.\n" + \
              "type_ input set to 0 (mesh-rectangular)."
    
    
    if (origin == None):
        origin = Rhino.Geometry.Point3d(0, 0, 0)
    # send the origin of this component ("Terrain Generator") to sc.sticky, in order for it be used in the "OSM search" component
    sc.sticky["gismo_terrainGeneratorComp_origin"] = origin
    
    
    if (standThickness == None):
        standThickness = 0  # no stand will be created
    elif (standThickness < 0):
        standThickness = 0
        print "standThickness_ input can not be lower than 0. It can only be either 0 (no stand) or higher.\n" + \
              "standThickness_ input set to 0 (no stand)."
    
    
    if (numOfContours == None):
        numOfContours = 10  # default
    elif (numOfContours < 0):
        numOfContours = 0
        print "numOfContours_ input can not be lower than 0. It can only be either 0 (no elevation contours created) or higher.\n" + \
              "numOfContours_ input set to 0 (no elevation contours will be created)."
    
    
    if (maxVisibilityRadiusM == None):
        maxVisibilityRadiusM = 200  # default in meters
    elif (maxVisibilityRadiusM >= 20) and (maxVisibilityRadiusM < 200):
        maxVisibilityRadiusM = 200  # values less than 150m can download invalid .tif file from opentopography.org. So the .tif file will always be downloaded with the minimal radius of 200 meters
    elif (maxVisibilityRadiusM < 20):
        maxVisibilityRadiusM = gridSize = source = sourceLabel = _type = typeLabel = origin = northRad = northDeg = standThickness = numOfContours = workingSubFolderPath = downloadTSVLink = unitConversionFactor = unitConversionFactor2 = None
        validInputData = False
        printMsg = "radius_ input only supports values equal or larger than 20 meters."
        return maxVisibilityRadiusM, gridSize, source, sourceLabel, _type, typeLabel, origin, northRad, northDeg, standThickness, numOfContours, workingSubFolderPath, downloadTSVLink, unitConversionFactor, unitConversionFactor2, validInputData, printMsg
    elif (maxVisibilityRadiusM > 100000):
        maxVisibilityRadiusM = gridSize = source = sourceLabel = _type = typeLabel = origin = northRad = northDeg = standThickness = numOfContours = workingSubFolderPath = downloadTSVLink = unitConversionFactor = unitConversionFactor2 = None
        validInputData = False
        printMsg = "Radii longer than 100 000 meters (100 kilometers) are not supported, due to possibility of crashing the Rhino.\n" + \
                   " \n" + \
                   "ATTENTION!!! Have in mind that even radii of a couple of thousands of meters may require stronger PC configurations and 64 bit version of Rhino 5. Otherwise Rhino 5 may crash."
        return maxVisibilityRadiusM, gridSize, source, sourceLabel, _type, typeLabel, origin, northRad, northDeg, standThickness, numOfContours, workingSubFolderPath, downloadTSVLink, unitConversionFactor, unitConversionFactor2, validInputData, printMsg
    
    #arcAngleD = math.degrees( math.atan( maxVisibilityRadiusM / (6371000+elevation) ) )  # assumption of Earth being a sphere
    #arcLength = (arcAngleD*math.pi*R)/180
    # correction of maxVisibilityRadiusM length due to light refraction can not be calculated, so it is assumed that arcLength = maxVisibilityRadiusM. maxVisibilityRadiusM variable will be used from now on instead of arcLength.
    
    
    if (north == None):
        northRad = 0  # default, in radians
        northVec = Rhino.Geometry.Vector3d(0,1,0)
    else:
        try:  # check if it's a number
            north = float(north)
            if north < 0 or north > 360:
                maxVisibilityRadiusM = gridSize = source = sourceLabel = _type = typeLabel = origin = northRad = northDeg = standThickness = numOfContours = workingSubFolderPath = downloadTSVLink = unitConversionFactor = unitConversionFactor2 = None
                validInputData = False
                printMsg = "Please input north angle value from 0 to 360."
                return maxVisibilityRadiusM, gridSize, source, sourceLabel, _type, typeLabel, origin, northRad, northDeg, standThickness, numOfContours, workingSubFolderPath, downloadTSVLink, unitConversionFactor, unitConversionFactor2, validInputData, printMsg
        except Exception, e:  # check if it's a vector
            north.Unitize()
        
        northRad, northVec = gismo_preparation.angle2northClockwise(north)
    northVec.Unitize()
    northDeg = int(360-math.degrees(northRad))
    if northDeg == 360: northDeg = 0
    
    
    # there is no workingFolder_ input. So files will always be saved to "Gismo Gismo"'s gismoFolder_
    gismoFolderPath = sc.sticky["gismo_gismoFolder"]
    workingSubFolderPath = os.path.join(gismoFolderPath, "terrain_files")
    folderCreatedSuccess = gismo_preparation.createFolder(workingSubFolderPath)
    if folderCreatedSuccess == False:
        maxVisibilityRadiusM = gridSize = source = sourceLabel = _type = typeLabel = origin = northRad = northDeg = standThickness = numOfContours = workingSubFolderPath = downloadTSVLink = unitConversionFactor = unitConversionFactor2 = None
        validInputData = False
        printMsg = "The file path you added to \"gismoFolder_\" input of Gismo Gismo component is invalid.\n" + \
                   "Input the string in the following format (example): c:\someFolder\gismo.\n" + \
                   "Or do not input anything, in which case a default Gismo folder will be used instead: C:\gismo."
        return maxVisibilityRadiusM, gridSize, source, sourceLabel, _type, typeLabel, origin, northRad, northDeg, standThickness, numOfContours, workingSubFolderPath, downloadTSVLink, unitConversionFactor, unitConversionFactor2, validInputData, printMsg
    
    if downloadTSVLink == None:
        downloadTSVLink = "https://raw.githubusercontent.com/stgeorges/terrainShadingMask/master/objFiles/0_terrain_shading_masks_download_links.tsv"
    
    #unitConversionFactor, unitSystemLabel = gismo_preparation.checkUnits()  # factor to convert Rhino document units to meters.
    unitConversionFactor = 1  # unitConversionFactor is always fixed to "1" to avoid problems when .obj files are exported from Rhino document (session) in one Units, and then imported in some other Rhino document (session) with different Units
    
    unitConversionFactor2, unitSystemLabel = gismo_preparation.checkUnits()
    
    
    validInputData = True
    printMsg = "ok"
    
    return maxVisibilityRadiusM, gridSize, source, sourceLabel, _type, typeLabel, origin, northRad, northDeg, standThickness, numOfContours, workingSubFolderPath, downloadTSVLink, unitConversionFactor, unitConversionFactor2, validInputData, printMsg


def distanceBetweenTwoPoints(latitude1D, longitude1D, maxVisibilityRadiusM):
    # "Distance/bearing between two points (inverse solution)" by Vincenty solution
    # based on JavaScript code made by Chris Veness
    # http://www.movable-type.co.uk/scripts/latlong-vincenty.html
    
    # setting the latitude2D, longitude2D according to SRTM latitude range boundaries (-56 to 60)
    if latitude1D >= 0:
        # northern hemishere:
        latitude2D = 60
    elif latitude1D < 0:
        # southern hemishere:
        latitude2D = -56
    longitude2D = longitude1D
    
    # for WGS84:
    a = 6378137  # equatorial radius, meters
    b = 6356752.314245  # polar radius, meters
    f = 0.00335281066474  # flattening (ellipticity, oblateness) parameter = (a-b)/a, dimensionless
    
    latitude1R = math.radians(latitude1D)
    latitude2R = math.radians(latitude2D)
    longitude1R = math.radians(longitude1D)
    longitude2R = math.radians(longitude2D)
    
    L = longitude2R - longitude1R
    tanU1 = (1-f) * math.tan(latitude1R)
    cosU1 = 1 / math.sqrt((1 + tanU1*tanU1))
    sinU1 = tanU1 * cosU1
    tanU2 = (1-f) * math.tan(latitude2R)
    cosU2 = 1 / math.sqrt((1 + tanU2*tanU2))
    sinU2 = tanU2 * cosU2
    longitudeR = L
    longitudeR_ = 0
    
    for i in range(100):
        sinLongitudeR = math.sin(longitudeR)
        cosLongitudeR = math.cos(longitudeR)
        sinSqSigma = (cosU2*sinLongitudeR) * (cosU2*sinLongitudeR) + (cosU1*sinU2-sinU1*cosU2*cosLongitudeR) * (cosU1*sinU2-sinU1*cosU2*cosLongitudeR)
        sinSigma = math.sqrt(sinSqSigma)
        cosSigma = sinU1*sinU2 + cosU1*cosU2*cosLongitudeR
        sigma = math.atan2(sinSigma, cosSigma)
        sinBearingAngleR = cosU1 * cosU2 * sinLongitudeR / sinSigma
        cosSqBearingAngleR = 1 - sinBearingAngleR*sinBearingAngleR
        if cosSqBearingAngleR == 0:
            # if distanceM is measured along the equator line (latitude1D = latitude2D = 0, longitude1D != longitude2D != 0)
            cos2SigmaM = 0
        else:
            cos2SigmaM = cosSigma - 2*sinU1*sinU2/cosSqBearingAngleR
        C = f/16*cosSqBearingAngleR*(4+f*(4-3*cosSqBearingAngleR))
        longitudeR_ = longitudeR
        longitudeR = L + (1-C) * f * sinBearingAngleR * (sigma + C*sinSigma*(cos2SigmaM+C*cosSigma*(-1+2*cos2SigmaM*cos2SigmaM)))
    
    uSq = cosSqBearingAngleR * (a*a - b*b) / (b*b)
    A = 1 + uSq/16384*(4096+uSq*(-768+uSq*(320-175*uSq)))
    B = uSq/1024 * (256+uSq*(-128+uSq*(74-47*uSq)))
    deltaSigma = B*sinSigma*(cos2SigmaM+B/4*(cosSigma*(-1+2*cos2SigmaM*cos2SigmaM) - B/6*cos2SigmaM*(-3+4*sinSigma*sinSigma)*(-3+4*cos2SigmaM*cos2SigmaM)))
    
    distanceM = b*A*(sigma-deltaSigma)  # in meters
    
    bearingAngleForwardR = math.atan2(cosU2*sinLongitudeR,  cosU1*sinU2-sinU1*cosU2*cosLongitudeR)
    bearingAngleReverseR = math.atan2(cosU1*sinLongitudeR, -sinU1*cosU2+cosU1*sinU2*cosLongitudeR)
    
    bearingAngleForwardD = math.degrees(bearingAngleForwardR)
    bearingAngleReverseD = math.degrees(bearingAngleReverseR)
    
    
    if latitude1D >= 0:
        SRTMlimit = "60 North"
    elif latitude1D < 0:
        SRTMlimit = "-56 South"
    
    if distanceM < 200:
        correctedMaskRadiusM = "dummy"
        validVisibilityRadiusM = False
        printMsg = "This component dowloads free topography data from opentopography.org in order to create a terrain for the chosen _location.\n" + \
                   "But mentioned free topography data has limits: from -56 South to 60 North latitude.\n" + \
                   "The closer the location is to upper mentioned boundaries, the inputted \"radius_\" value may have be shrank to make sure that the boundaries are not exceeded.\n" + \
                   "In this case the _location you chose is very close (less than 20 meters) to the %s latitude boundary.\n" % SRTMlimit + \
                   "It is not possible to create a terrain for locations less than 200 meters close to mentioned boundary, as this _location is.\n" + \
                   "Try using the Ladybug \"Terrain Generator\" component instead."
    else:
        # shortening the maxVisibilityRadiusM according to the distance remained to the SRTM latitude range boundaries (-56 to 60)
        if distanceM < maxVisibilityRadiusM:
            print "distanceM < maxVisibilityRadiusM: ", distanceM < maxVisibilityRadiusM
            print "distanceM, maxVisibilityRadiusM: ", distanceM, maxVisibilityRadiusM
            correctedMaskRadiusM = int(distanceM)  # int(distanceM) will always perform the math.floor(distanceM)
            validVisibilityRadiusM = False
            printMsg = "This component downloads free topography data from opentopography.org in order to create a terrain for the chosen _location.\n" + \
                       "But mentioned free topography data has limits: from -56 South to 60 North latitude.\n" + \
                       "The closer the location is to upper mentioned boundaries, the inputted \"radius_\" value may have to be shrank to make sure that the boundaries are not exceeded.\n" + \
                       "In this case the _location you chose is %s meters away from the %s latitude boundary.\n" % (correctedMaskRadiusM, SRTMlimit) + \
                       " \n" + \
                       "Please supply the \"radius_\" input with value: %s.\n" % correctedMaskRadiusM
        elif distanceM >= maxVisibilityRadiusM:
            correctedMaskRadiusM = maxVisibilityRadiusM
            validVisibilityRadiusM = True
            printMsg = "ok"
    
    return correctedMaskRadiusM, validVisibilityRadiusM, printMsg


def destinationLatLon(latitude1D, longitude1D, maxVisibilityRadiusM):
    # "Destination point given distance and bearing from start point" by Vincenty solution
    # based on JavaScript code made by Chris Veness
    # http://www.movable-type.co.uk/scripts/latlong-vincenty.html
    
    # for WGS84:
    a = 6378137  # equatorial radius, meters
    b = 6356752.314245  # polar radius, meters
    f = 0.00335281066474  # flattening (ellipticity, oblateness) parameter = (a-b)/a, dimensionless
    
    bearingAnglesR = [math.radians(0), math.radians(180), math.radians(270), math.radians(90)]  # top, bottom, left, right
    latitudeLongitudeRegion = []
    for bearingAngle1R in bearingAnglesR:
        latitude1R = math.radians(latitude1D)
        longitude1R = math.radians(longitude1D)
        sinbearingAngle1R = math.sin(bearingAngle1R)
        cosbearingAngle1R = math.cos(bearingAngle1R)
        tanU1 = (1 - f) * math.tan(latitude1R)
        cosU1 = 1 / math.sqrt(1 + tanU1 * tanU1)
        sinU1 = tanU1 * cosU1
        sigma1 = math.atan2(tanU1, cosbearingAngle1R)
        sinBearingAngle1R = cosU1 * sinbearingAngle1R
        cosSqBearingAngle1R = 1 - (sinBearingAngle1R * sinBearingAngle1R)
        uSq = cosSqBearingAngle1R * (a * a - (b * b)) / (b * b)
        A = 1 + uSq / 16384 * (4096 + uSq * (-768 + uSq * (320 - (175 * uSq))))
        B = uSq / 1024 * (256 + uSq * (-128 + uSq * (74 - (47 * uSq))))
        sigma = maxVisibilityRadiusM / (b * A)  # maxVisibilityRadiusM in meters
        sigma_ = 0
        while abs(sigma - sigma_) > 1e-12:
            cos2sigmaM = math.cos(2 * sigma1 + sigma)
            sinsigma = math.sin(sigma)
            cossigma = math.cos(sigma)
            deltaSigma = B * sinsigma * (cos2sigmaM + B / 4 * (cossigma * (-1 + 2 * cos2sigmaM * cos2sigmaM) - (B / 6 * cos2sigmaM * (-3 + 4 * sinsigma * sinsigma) * (-3 + 4 * cos2sigmaM * cos2sigmaM))))
            sigma_ = sigma
            sigma = maxVisibilityRadiusM / (b * A) + deltaSigma
        
        tmp = sinU1 * sinsigma - (cosU1 * cossigma * cosbearingAngle1R)
        latitude2R = math.atan2(sinU1 * cossigma + cosU1 * sinsigma * cosbearingAngle1R, (1 - f) * math.sqrt(sinBearingAngle1R * sinBearingAngle1R + tmp * tmp))
        longitudeR = math.atan2(sinsigma * sinbearingAngle1R, cosU1 * cossigma - (sinU1 * sinsigma * cosbearingAngle1R))
        C = f / 16 * cosSqBearingAngle1R * (4 + f * (4 - (3 * cosSqBearingAngle1R)))
        L = longitudeR - ((1 - C) * f * sinBearingAngle1R * (sigma + C * sinsigma * (cos2sigmaM + C * cossigma * (-1 + 2 * cos2sigmaM * cos2sigmaM))))
        longitude2R = (longitude1R + L + 3 * math.pi) % (2 * math.pi) - math.pi  # normalise to -180...+180
        bearingAngle2R = math.atan2(sinBearingAngle1R, -tmp)
        
        latitude2D = math.degrees(latitude2R)
        longitude2D = math.degrees(longitude2R)
        bearingAngle2D = math.degrees(bearingAngle2R)
        if bearingAngle2D < 0:
            bearingAngle2D = 360-abs(bearingAngle2D)
        
        latitudeLongitudeRegion.append(latitude2D)
        latitudeLongitudeRegion.append(longitude2D)
    
    # latitude positive towards north, longitude positive towards east
    latitudeTopD, dummyLongitudeTopD, latitudeBottomD, dummyLongitudeBottomD, dummyLatitudeLeftD, longitudeLeftD, dummyLatitudeRightD, longitudeRightD = latitudeLongitudeRegion
    
    return latitudeTopD, dummyLongitudeTopD, latitudeBottomD, dummyLongitudeBottomD, dummyLatitudeLeftD, longitudeLeftD, dummyLatitudeRightD, longitudeRightD


def import_export_origin_0_0_0_and_terrainShadingMask_from_objFile(importExportObj, objFilePath, fileNameIncomplete, heightM, minVisibilityRadiusM, maxVisibilityRadiusM, elevationM=None, shadingMaskSrf=None, origin=None):
        
        objFilePath2 = chr(34) + objFilePath + chr(34)
        
        if importExportObj == "importObj":
            # import origin_0_0_0, terrainShadingMask from .obj file
            sc.doc = Rhino.RhinoDoc.ActiveDoc
            
            commandString = "_-Import %s _Enter" % objFilePath2; echo = False
            importObjSuccess = rs.Command(commandString, echo)
            
            terrainShadingMaskUnjoined = []
            objIds = rs.LastCreatedObjects(False)
            if objIds != None:
                for rhinoId in objIds:
                    obj = sc.doc.Objects.Find(rhinoId).Geometry
                    if isinstance(obj, Rhino.Geometry.Point):
                        origin_0_0_0 = Rhino.Geometry.Point3d(obj.Location) # convert Point to Point3d
                    elif isinstance(obj, Rhino.Geometry.Brep):
                        terrainShadingMaskUnjoined.append(obj)
                rs.DeleteObjects(objIds)
                sc.doc = ghdoc
                
                # join brep objects
                tol = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
                terrainShadingMask = Rhino.Geometry.Brep.MergeBreps(terrainShadingMaskUnjoined,tol)  # terrainShadingMask joined
            elif objIds == None:
                # this happens when a user opened a new Rhino file, while runIt_ input has been set to True. In this case the rs.LastCreatedObjects function returns: None
                terrainShadingMask = origin_0_0_0 = None
        
        elif importExportObj == "exportObj":
            # export the generated terrain shading mask to .obj file
            sc.doc = Rhino.RhinoDoc.ActiveDoc
            objIds = []
            objs = [shadingMaskSrf, Rhino.Geometry.Point(origin)]
            for obj in objs:
                objId = sc.doc.Objects.Add(obj)
                objIds.append(objId)
            rs.SelectObjects(objIds)  # select objects for _-Export
            commandString = "_-testMakeValidForV2 _Enter"  # convert the terrainShadingMaskUnscaledUnrotated from Surface of Revolution to NURBS Surface
            commandString2 = "_-Export %s Geometry=NURBS _Enter" % objFilePath2; echo = False
            exportObjSuccess = rs.Command(commandString, echo)
            exportObjSuccess2 = rs.Command(commandString2, echo)
            rs.DeleteObjects(objIds)  # delete the objects added to Rhino document, after the _-Export
            sc.doc = ghdoc
            
            # change exported .obj file heading
            objFileLines = []
            myFile = open(objFilePath,"r")
            for line in myFile.xreadlines():
                objFileLines.append(line)
            myFile.close()
            
            
            locationNameCorrected_latitude_longitude = (fileNameIncomplete.split("_TERRAIN_MASK")[0]).replace("_"," ")
            
            nowUTC = datetime.datetime.utcnow()  # UTC date and time
            UTCdateTimeString = str(nowUTC.year) + "-" + str(nowUTC.month) + "-" + str(nowUTC.day) + " " + str(nowUTC.hour) + ":" + str(nowUTC.minute) + ":" + str(nowUTC.second)
            
            myFile = open(objFilePath,"w")
            for line in objFileLines:
                if line == "# Rhino\n":
                    line = "# Rhino\n# Terrain shading mask generated by Grasshopper Gismo plugin\n# True North direction is set to the Y axis\n# Location: %s\n# Elevation: %s m\n# Visibility radius: %s-%s km\n# Mask radius: 200 document units\n# Created on (UTC): %s\n" % (locationNameCorrected_latitude_longitude, elevationM, minVisibilityRadiusM/1000, int(maxVisibilityRadiusM/1000), UTCdateTimeString)
                else:
                    pass
                myFile.write(line)
            myFile.close()
            
            
            terrainShadingMask = origin_0_0_0 = None  # not needed for "exportObj"
        
        return terrainShadingMask, origin_0_0_0


def checkObjRasterFile(fileNameIncomplete, workingSubFolderPath, downloadTSVLink, heightM, minVisibilityRadiusM, maxVisibilityRadiusM, maskStyleLabel):
    
    # convert the float to integer if minVisibilityRadiusM == 0 (to avoid "0.0" in the .obj fileName)
    if minVisibilityRadiusM == 0:
        minVisibilityRadiusKM = 0
    else:
        minVisibilityRadiusKM = minVisibilityRadiusM/1000
    
    fileName = fileNameIncomplete + "_visibility=" + str(minVisibilityRadiusKM) + "-" + str(round(maxVisibilityRadiusM/1000, 2)) + "KM"
    fileName2 = fileNameIncomplete + "_visibility=" + str(round(maxVisibilityRadiusM/1000, 2)) + "KM"
    objFileNamePlusExtension = fileName + "_" + maskStyleLabel + ".obj"
    rasterFileNamePlusExtension = fileName2 + ".tif"
    rasterReprojectedFileNamePlusExtension = fileName2 + "_reprojected" + ".tif"
    tsvFileNamePlusExtension = "0_terrain_shading_masks_download_links" + ".tsv"
    vrtFileNamePlusExtension = fileName + "_" + maskStyleLabel + "_reprojected" + ".vrt"
    
    objFilePath = os.path.join(workingSubFolderPath, objFileNamePlusExtension)
    rasterFilePath = os.path.join(workingSubFolderPath, rasterFileNamePlusExtension)
    rasterReprojectedFilePath = os.path.join(workingSubFolderPath, rasterReprojectedFileNamePlusExtension)
    tsvFilePath = os.path.join(workingSubFolderPath, tsvFileNamePlusExtension)
    vrtFilePath = os.path.join(workingSubFolderPath, vrtFileNamePlusExtension)
    
    
    # chronology labels:  I, II, 1, 2, A, B, a, b
    
    ##### I) check if .obj file exist:
    objFileAlreadyExists = os.path.exists(objFilePath)
    if objFileAlreadyExists == True:
        # .obj file already created. Import it
        terrainShadingMask, origin_0_0_0 = import_export_origin_0_0_0_and_terrainShadingMask_from_objFile("importObj", objFilePath, fileNameIncomplete, heightM, minVisibilityRadiusM, maxVisibilityRadiusM)
        if (terrainShadingMask != None) and (origin_0_0_0 != None):
            # extract "elevationM" data from the .obj file
            myFile = open(objFilePath,"r")
            for line in myFile.xreadlines():
                if "Elevation" in line:
                    splittedLine = line.split(" ")
                    elevationM = splittedLine[2]
                    break
            else:
                elevationM = None  # if somebody opened the .obj file and deleted the heading for some reason
            myFile.close()
            
            rasterFilePath = "needless"
            valid_Obj_or_Raster_file = True
            printMsg = "ok"
        elif (terrainShadingMask == None) and (origin_0_0_0 == None):
            elevationM = None
            rasterFilePath = "needless"  # dummy
            valid_Obj_or_Raster_file = False
            printMsg = "You opened a new Rhino file while \"runIt_\" input has been set to True.\n" + \
                       "This component relies itself on Rhino document, and opening a new Rhino file results in component not working properly.\n" + \
                       "Just set the \"runIt_\" input back to False, and then again to True, to make it work again, with the newest Rhino file."
    elif objFileAlreadyExists == False:
        ##### II).obj file can not be found in "workingFolderPath" folder (example: "C:\gismo\terrain shading masks").
        #####     check if .obj file is listed in "0_terrain_shading_masks_download_links.tsv"  file (download the "0_terrain_shading_masks_download_links.tsv" file first)
        terrainShadingMask = origin_0_0_0 = elevationM = None
        
        # connectedToInternet first check
        connectedToInternet1 = System.Net.NetworkInformation.NetworkInterface.GetIsNetworkAvailable()
        if connectedToInternet1 == False:
            # connectedToInternet second check
            try:
                client = System.Net.WebClient()
                client.OpenRead("http://www.google.com")
                connectedToInternet = True
            except:
                connectedToInternet = False
                # you are not connected to the Internet
        elif connectedToInternet1 == True:
            # no need for connectedToInternet second check
            connectedToInternet = True
        
        
        if connectedToInternet == False:
            # you are NOT connected to the Internet, exit this function
            rasterFilePath = "download failed"
            terrainShadingMask = origin_0_0_0 = None
            valid_Obj_or_Raster_file = False
            printMsg = "This component requires you to be connected to the Internet, in order to create a terrain.\n" + \
                       "Please do connect, then rerun the component (set \"_runIt\" to False, then to True)."
        elif connectedToInternet == True:
            # you ARE connected to the Internet
            
            # download "0_terrain_shading_masks_download_links.tsv" (no need to check if it is already in the "workingSubFolderPath" as a newer version of "0_terrain_shading_masks_download_links.tsv" file may exist online)
            tsvFileDownloaded = gismo_preparation.downloadFile(downloadTSVLink, tsvFilePath)
            
            if tsvFileDownloaded == False:
                #### II.2 "0_terrain_shading_masks_download_links.tsv" has NOT been downloaded
                if downloadUrl_ != None:
                    ### II.2.A inputted downloadUrl_ is either not valid, or the "0_terrain_shading_masks_download_links.tsv" file is not uploaded at that address
                    rasterFilePath = "download failed"
                    terrainShadingMask = origin_0_0_0 = None
                    valid_Obj_or_Raster_file = False
                    printMsg = "The address plugged into downloadUrl_ input is incorrect.\n" + \
                               "Try unplugging it, so that the component tries to use its default address."
                elif downloadUrl_ == None:
                    ### II.2.B default downloadUrl_ is not valid anymore, nevertheless try ignoring the "0_terrain_shading_masks_download_links.tsv" file and create the .obj file from a .tif file
                    ### it may also happen that "Error 404.htm" page will be downloaded as "0_terrain_shading_masks_download_links.tsv" file
                    ### go to switch
                    pass
            
            elif tsvFileDownloaded == True:
                #### II.1 "0_terrain_shading_masks_download_links.tsv" IS downloaded
                
                # checking if .obj file has been listed in "0_terrain_shading_masks_download_links.tsv"
                myFile = open(tsvFilePath,"r")
                downloadObjLink = None
                for line in myFile.xreadlines():
                    if fileName in line:
                        splittedLineL = line.split("\t")  # split the line with "tab"
                        for string in splittedLineL:
                            if "http" in string:
                                downloadObjLink_unstripped = string.split("\n")[0]  # split the downloadObjLink and "\n"
                                downloadObjLink = System.String.strip(downloadObjLink_unstripped)  # remove white spaces from the beginning, end of the downloadObjLink
                        break
                myFile.close()
                
                if downloadObjLink != None:
                    ### II.1.A .obj file IS listed in "0_terrain_shading_masks_download_links.tsv", so download it
                    objFileDownloadedDummy = gismo_preparation.downloadFile(downloadObjLink, objFilePath)
                    terrainShadingMask, origin_0_0_0 = import_export_origin_0_0_0_and_terrainShadingMask_from_objFile("importObj", objFilePath, fileNameIncomplete, heightM, minVisibilityRadiusM, maxVisibilityRadiusM)
                    rasterFilePath = "needless"
                    valid_Obj_or_Raster_file = True
                    printMsg = "ok"
                elif downloadObjLink == None:
                    ### II.1.B .obj file is NOT listed in "0_terrain_shading_masks_download_links.tsv", try to create it from a .tif file
                    ### go to switch
                    pass
    
    ### switch
    if ((objFileAlreadyExists == False) and (connectedToInternet == True) and (tsvFileDownloaded == False) and (downloadUrl_ == None))   or   ((objFileAlreadyExists == False) and (connectedToInternet == True) and (tsvFileDownloaded == True) and (downloadObjLink == None)):
        ### .obj file could not be found, due to one of the following two reasons:
        ### - default downloadUrl_ is not valid anymore (II.2.B); or
        ### - .obj file is NOT listed in "0_terrain_shading_masks_download_links.tsv" (II.1.B);
        ### so try to create an .obj file from a .tif file
        terrainShadingMask = origin_0_0_0 = "needs to be calculated"
        rasterFileAlreadyExists = os.path.exists(rasterFilePath)
        if rasterFileAlreadyExists == True:
            ## .tif file already downloaded previously
            valid_Obj_or_Raster_file = True
            printMsg = "ok"
        if rasterFileAlreadyExists == False:
            ## .tif file has not been downloaded up until now, download it
            
            # first check the location before download, so that it fits the opentopography.org limits (-56 to 60(59.99999 used instead of 60) latitude):
            if locationLatitudeD > 59.99999:
                # location beyond the -56 to 60 latittude limits
                # (correctedMaskRadiusM < 1) or (correctedMaskRadiusM < maxVisibilityRadiusM)
                terrainShadingMask = origin_0_0_0 = None
                valid_Obj_or_Raster_file = False
                rasterFilePath = "needless"  # dummy
                printMsg = "This component dowloads free topography data from opentopography.org in order to create a terrain for the chosen _location.\n" + \
                           "But mentioned free topography data has its limits: from -56 South to 60 North latitude.\n" + \
                           "Your _location's latitude exceeds the upper mentioned limits.\n" + \
                           " \n" + \
                           "Try using the Ladybug \"Terrain Generator\" component instead."
            else:
                # location within the -56 to 60 latittude limits
                # correct (shorten) the maxVisibilityRadiusM according to the distance remained to the SRTM latitude range boundaries (-56 to 60)
                correctedMaskRadiusM, validVisibilityRadiusM, printMsg = distanceBetweenTwoPoints(locationLatitudeD, locationLongitudeD, maxVisibilityRadiusM)
                if validVisibilityRadiusM == True:
                    # (correctedMaskRadiusM >= maxVisibilityRadiusM)
                    latitudeTopD, dummyLongitudeTopD, latitudeBottomD, dummyLongitudeBottomD, dummyLatitudeLeftD, longitudeLeftD, dummyLatitudeRightD, longitudeRightD = destinationLatLon(locationLatitudeD, locationLongitudeD, correctedMaskRadiusM)
                    # generate download link for raster region (based on: http://www.opentopography.org/developers)
                    downloadRasterLink_withCorrectedMaskRadiusKM = "http://opentopo.sdsc.edu/otr/getdem?demtype=SRTMGL1&west=%s&south=%s&east=%s&north=%s&outputFormat=GTiff" % (longitudeLeftD,latitudeBottomD,longitudeRightD,latitudeTopD)  # 1 arc second
                    
                    # new rasterFileNamePlusExtension and rasterFilePath corrected according to new correctedMaskRadiusM
                    rasterFileNamePlusExtension_withCorrectedMaskRadiusKM = fileNameIncomplete + "_visibility=" + str(round(maxVisibilityRadiusM/1000, 2)) + "KM" + ".tif"  # rasterFileNamePlusExtension_withCorrectedMaskRadiusKM will always be used instead of rasterFilePath from line 647 !!!
                    rasterFilePath_withCorrectedMaskRadiusKM = os.path.join(workingSubFolderPath, rasterFileNamePlusExtension_withCorrectedMaskRadiusKM)
                    tifFileDownloaded = gismo_preparation.downloadFile(downloadRasterLink_withCorrectedMaskRadiusKM, rasterFilePath_withCorrectedMaskRadiusKM)
                    if tifFileDownloaded:
                        terrainShadingMask = origin_0_0_0 = None
                        valid_Obj_or_Raster_file = True
                        printMsg = "ok"
                    else:
                        rasterFilePath = "download failed"
                        terrainShadingMask = origin_0_0_0 = elevationM = None
                        valid_Obj_or_Raster_file = False
                        printMsg = "This component requires topography data to be downloaded from opentopography.org as a prerequisite for creating a terrain. It has just failed to do that. Try the following two fixes:\n" + \
                                   " \n" + \
                                   "1) Sometimes due to large number of requests, the component fails to download the topography data even if opentopography.org website and their services are up and running.\n" + \
                                   "In this case, wait a couple of seconds and try reruning the component.\n" + \
                                   " \n" + \
                                   "2) opentopography.org website could be up and running, but their SRTM service may be down (this already happened before).\n" + \
                                   "Try again in a couple of hours.\n" + \
                                   " \n" + \
                                   "If each of two mentioned advices fails, open a new topic about this issue on: www.grasshopper3d.com/group/gismo/forum."
                
                elif validVisibilityRadiusM == False:
                    # (correctedMaskRadiusM < 1) or (correctedMaskRadiusM < maxVisibilityRadiusM)
                    elevationM = None
                    valid_Obj_or_Raster_file = False
                    rasterFilePath = "needless"  # dummy
                    #printMsg - from distanceBetweenTwoPoints function
    
    
    return terrainShadingMask, origin_0_0_0, fileName, objFilePath, rasterFilePath, rasterReprojectedFilePath, rasterReprojectedFileNamePlusExtension, vrtFilePath, elevationM, valid_Obj_or_Raster_file, printMsg


def createTerrainMeshBrep2(locationLatitudeD, locationLongitudeD, maxVisibilityRadiusM, gridSize, unitConversionFactor2):
    
    # create "terrainMesh" and "terrrainBrep" from GoogleMaps data
    
    # find cellsize based on radius_ and gridSize_ inputs
    latitudeTopD, longitudeTopD, latitudeBottomD, longitudeBottomD, latitudeLeftD, longitudeLeftD, latitudeRightD, longitudeRightD = destinationLatLon(locationLatitudeD, locationLongitudeD, maxVisibilityRadiusM)
    topLeftPointLatitude = latitudeTopD
    topLeftPointLongitude = longitudeLeftD
    
    diameterM = 2 * maxVisibilityRadiusM
    numOfPtsInX = int(diameterM / gridSize)
    numOfPtsInY = numOfPtsInX
    
    numOfFieldsMirrored = ((numOfPtsInX-1)/2)
    cellsizeX_M = maxVisibilityRadiusM / numOfFieldsMirrored   # in meters, for 22x22 elevation points (484 points total < 512 allowed), there is 10.5 fields from each side of X or Y axis
    cellsizeY_M = cellsizeX_M 
    
    # generate lat-lon pairs for url query
    elevationPts_lat_lon = []
    scaleFactor = 1
    for k in range(numOfPtsInY):
        for i in range(numOfPtsInX):
            distanceX = - k*cellsizeX_M  # in Rhino units
            distanceY = i*cellsizeY_M  # in Rhino units
            
            distanceX = distanceX * scaleFactor
            distanceY = distanceY * scaleFactor
            if distanceX == 0:
                latitudeTopD1 = topLeftPointLatitude
            elif distanceX != 0:
                latitudeTopD1, longitudeTopD1, latitudeBottomD1, longitudeBottomD1, latitudeLeftD1, longitudeLeftD1, latitudeRightD1, longitudeRightD1 = destinationLatLon(topLeftPointLatitude, topLeftPointLongitude, distanceX)
            
            if distanceY == 0:
                longitudeRightD2 = topLeftPointLongitude
            elif distanceY != 0:
                latitudeTopD2, longitudeTopD2, latitudeBottomD2, longitudeBottomD2, latitudeLeftD2, longitudeLeftD2, latitudeRightD2, longitudeRightD2 = destinationLatLon(topLeftPointLatitude, topLeftPointLongitude, distanceY)
            elevationPt_latitude = latitudeTopD1
            elevationPt_longitude = longitudeRightD2
            elevationPt = Rhino.Geometry.Point3d(elevationPt_longitude, elevationPt_latitude, 0)
            
            elevationPts_lat_lon.append(elevationPt)
    
    # create all url queries
    numOfItemsPerList = 256  # which is half of 512. 256 seems to be the maximal number of allowed elevationPts per single query if "access_key" is not supplied to the end of the URL call to google maps
    numOfItemsPerList = max(1, numOfItemsPerList)
    elevationPts_lat_lon_LL = list(elevationPts_lat_lon[i:i+numOfItemsPerList] for i in xrange(0, len(elevationPts_lat_lon), numOfItemsPerList))  # from http://stackoverflow.com/a/1751478
    #print "len(elevationPts_lat_lon_LL): ", len(elevationPts_lat_lon_LL)  # this is also the number of "googleMapsElevations_nn.txt" files
    
    googleMapsElevationRequest_url_L = []
    for subList in elevationPts_lat_lon_LL:
        if len(subList) > 0:
            locations_string = ""
            for elevationPt in subList:
                locations_string += str(elevationPt.Y) + "," + str(elevationPt.X) + "|"
            googleMapsElevationRequest_url = "http://maps.googleapis.com/maps/api/elevation/json?locations=" + locations_string[:-1] + "&sensor=false"  # [:-1] to remove the last "|"
            googleMapsElevationRequest_url_L.append(googleMapsElevationRequest_url)
    
    # download the file "googleMapsElevations_nn.txt" files
    downloadedFilePath_L = []
    for index,googleMapsElevationRequest_url in enumerate(googleMapsElevationRequest_url_L):
        downloadedFilePath = "D:\za brisanje\osm\googleMapsElevations_%s.txt" % index
        if os.path.exists(downloadedFilePath):
            downloadedFilePath_L.append(downloadedFilePath)
        else:
            downloadFileSuccess = gismo_preparation.downloadFile(googleMapsElevationRequest_url, downloadedFilePath)
            print "downloadFileSuccess: ", downloadFileSuccess
            if (downloadFileSuccess == True):
                downloadedFilePath_L.append(downloadedFilePath)
    
    
    # extract elevation data from "googleMapsElevations.txt"
    googleMapsElevations = []
    for downloadedFilePath in downloadedFilePath_L:
        status = ""  # initial value
        myFile = open(downloadedFilePath,"r")
        for line in myFile.xreadlines():
            if "elevation" in line:
                elevationValue_unstripped = line.split(":")[-1]
                elevationValue = elevationValue_unstripped[:-2].strip()  # remove "," from the end. And empty spaces from beginning
                googleMapsElevations.append(float(elevationValue))
            
            if "status" in line:
                # https://developers.google.com/maps/documentation/elevation/intro#ElevationResponses
                statusLine_stripped = line.strip()
                statusLine_splitted = statusLine_stripped.split(":")
                status = statusLine_splitted[1].replace('"','')
                status = status.strip()
        #print "status=%s__" % status
    myFile.close()
    
    
    
    if (status != "OK"):  # only the last value of "status" will be taken into account
        terrainMesh = terrainBrep = locationPt = elevationM = None
        valid_GoogleMapsQuery = False
        printMsg = "The following error message has been raised:\n \n" + \
                   " %s\n \n" % status + \
                   "If upper error message is: \"OVER_QUERY_LIMIT\", then that means that you exceeded allowed daily data quota from Google Maps. Do the following:\n" + \
                   "a) Either decrease the \"_radius\" input/or increase the \"gridSize_\" input and try tomorrow,  or\n" + \
                   "b) Change the \"source_\" input to \"0\" (Open topography source instead of Google Maps). \"source_ = 1\" has much smaller allowed daily data quota than \"source_\" = 0.\n" + \
                   " \n" + \
                   "If this is not the raised error message, then post a question on Grasshopper forum, with a screenshot of your error message:\n" + \
                   "http://www.grasshopper #####"
        return terrainMesh, terrainBrep, locationPt, elevationM, valid_GoogleMapsQuery, printMsg
    else:
        scaleFactor = 0.01  # scale terrainMesh 100 times (should never be changed), meaning 1 meter in real life is 0.01 meters in Rhino document
        origin_0_0_0 = Rhino.Geometry.Point3d(0,0,0)  # always center the terrainMesh to 0,0,0 point
        topLeftPtX = origin_0_0_0.X - (numOfFieldsMirrored * cellsizeX_M/unitConversionFactor2 * scaleFactor)
        topLeftPtY = origin_0_0_0.Y + (numOfFieldsMirrored * cellsizeY_M/unitConversionFactor2 * scaleFactor)
        
        index = 0
        pts = []
        for k in range(numOfPtsInY):
            for i in range(numOfPtsInX):
                ptY = topLeftPtY - (k*cellsizeY_M/unitConversionFactor2 * scaleFactor)
                ptX = topLeftPtX + (i*cellsizeX_M/unitConversionFactor2 * scaleFactor)
                ptZ = googleMapsElevations[index]/unitConversionFactor2 * scaleFactor
                pt = Rhino.Geometry.Point3d(ptX, ptY, ptZ)
                pts.append(pt)
                index += 1
        
        terrainMesh = gismo_geometry.meshFromPoints(numOfPtsInX, numOfPtsInX, pts)
    
    
    # always create a terrain brep
    uDegree = min(3, numOfPtsInY - 1)
    vDegree = min(3, numOfPtsInX - 1)
    uClosed = False; vClosed = False
    terrainSurface = Rhino.Geometry.NurbsSurface.CreateThroughPoints(pts, numOfPtsInY, numOfPtsInX, uDegree, vDegree, uClosed, vClosed)
    terrainBrep = terrainSurface.ToBrep()
    
    
    # project origin_0_0_0 (locationPt) to terrainMesh
    safeHeightDummy = 10000/unitConversionFactor2  # in meters
    origin_0_0_0 = Rhino.Geometry.Point3d(0,0,0)  # always center the terrainMesh to 0,0,0 point
    elevatedOrigin = Rhino.Geometry.Point3d(origin_0_0_0.X, origin_0_0_0.Y, (origin_0_0_0.Z+safeHeightDummy)*scaleFactor)  # project origin_0_0_0 to terrainMesh
    ray = Rhino.Geometry.Ray3d(elevatedOrigin, Rhino.Geometry.Vector3d(0,0,-1))
    rayIntersectParam = Rhino.Geometry.Intersect.Intersection.MeshRay(terrainMesh, ray)
    locationPt = ray.PointAt(rayIntersectParam)
    
    elevationM = locationPt.Z/scaleFactor  # in rhino document units (not meters)
    elevationM = round(elevationM,2)
    
    
    # deleting
    del elevationPts_lat_lon_LL
    del googleMapsElevationRequest_url_L
    del pts
    gc.collect()
    
    valid_GoogleMapsQuery = True
    printMsg = "ok"
    
    return terrainMesh, terrainBrep, locationPt, elevationM, valid_GoogleMapsQuery, printMsg


def createTerrainMeshBrep(rasterFilePath, rasterReprojectedFilePath, locationLatitudeD, locationLongitudeD, maxVisibilityRadiusM, unitConversionFactor2):
    
    # create "terrainMesh" and "terrrainBrep" from Opentopography data
    
    # output crs data: outputCRS_UTMzone, northOrsouth
    # by http://stackoverflow.com/a/9188972/3137724 (link given by Even Rouault)
    outputCRS_UTMzone = (math.floor((locationLongitudeD + 180)/6) % 60) + 1
    if locationLatitudeD >= 0:
        # for northern hemisphere
        northOrsouth = "north"
    elif locationLatitudeD < 0:
        # for southern hemisphere
        northOrsouth = "south"
    
    # reproject raster
    utils = MapWinGIS.UtilsClass()
    resamplingMethod = "-r bilinear"
    bstrOptions = '-s_srs EPSG:4326 -t_srs "+proj=utm +zone=%s +%s +datum=WGS84 +ellps=WGS84" %s' % (int(outputCRS_UTMzone), northOrsouth, resamplingMethod)
    reprojectGridResult = MapWinGIS.UtilsClass.GDALWarp(utils, rasterFilePath, rasterReprojectedFilePath, bstrOptions, None)
    if (reprojectGridResult != True):
        convertErrorNo = MapWinGIS.GlobalSettingsClass().GdalLastErrorNo
        convertErrorMsg = MapWinGIS.GlobalSettingsClass().GdalLastErrorMsg
        convertErrorType = MapWinGIS.GlobalSettingsClass().GdalLastErrorType
        print "convertErrorNo: ", convertErrorNo
        print "convertErrorMsg: ", convertErrorMsg
        print "convertErrorType: ", convertErrorType
    
    # open the reprojected raster
    grid = MapWinGIS.GridClass()
    dataType = MapWinGIS.GridDataType.DoubleDataType
    fileTypeExtension = MapWinGIS.GridFileType.UseExtension
    inRam = True
    openGridSuccess = MapWinGIS.GridClass.Open(grid, rasterReprojectedFilePath, dataType, inRam, fileTypeExtension, None)
    if (openGridSuccess != True):
        gridErrorMsg = grid.ErrorMsg
        print "gridErrorMsg: ", gridErrorMsg
    
    # numOfRows, numOfColumns, cellsizeX, cellsizeY
    header = grid.Header
    numOfRows = header.NumberRows
    numOfColumns = header.NumberCols
    numOfCellsInX = numOfColumns
    numOfCellsInY = numOfRows
    cellsizeX = header.dX
    cellsizeY = header.dY
    
    # calculate the starting point (upper left corner) of terrain mesh
    scaleFactor = 0.01  # scale terrainMesh 100 times (should never be changed), meaning 1 meter in real life is 0.01 meters in Rhino document
    lowerLeftCornerCellCentroidXcoord = header.XllCenter
    lowerLeftCornerCellCentroidYcoord = header.YllCenter
    lowerLeftCornerXcoord = lowerLeftCornerCellCentroidXcoord - (cellsizeX/2)
    lowerLeftCornerYcoord = lowerLeftCornerCellCentroidYcoord - (cellsizeY/2)
    
    originPtProjected = gismo_osm.projectedLocationCoordinates(locationLatitudeD, locationLongitudeD)  # find the "origin" projected in Rhino document units for specific UTMzone
    
    terrainMeshLeftBottomPtX = (lowerLeftCornerXcoord/unitConversionFactor2) - (originPtProjected.X/unitConversionFactor2)
    terrainMeshLeftBottomPtY = (lowerLeftCornerYcoord/unitConversionFactor2) - (originPtProjected.Y/unitConversionFactor2)
    
    terrainMeshStartPtX = ( terrainMeshLeftBottomPtX )*scaleFactor
    terrainMeshStartPtY = ( terrainMeshLeftBottomPtY + ((abs(cellsizeX)/unitConversionFactor2)*numOfRows) )*scaleFactor
    
    pts = []
    # create terrainMesh from 1 arc-second format
    for k in xrange(numOfCellsInY):
        for i in xrange(numOfCellsInX):
            ptZ = grid.Value(i,k)
            pt = Rhino.Geometry.Point3d(terrainMeshStartPtX+(i*abs(cellsizeX/unitConversionFactor2)*scaleFactor), terrainMeshStartPtY-(k*abs(cellsizeY/unitConversionFactor2)*scaleFactor), ptZ/unitConversionFactor2*scaleFactor)
            pts.append(pt)
    
    closeGridSuccess = grid.Close()
    
    # always create a terrain mesh regardless of type_ input so that "elevationM" can be calculated on a mesh
    terrainMesh = gismo_geometry.meshFromPoints(numOfRows, numOfColumns, pts)
    
    
    # always create a terrain brep
    uDegree = min(3, numOfCellsInY - 1)
    vDegree = min(3, numOfCellsInX - 1)
    uClosed = False; vClosed = False
    terrainSurface = Rhino.Geometry.NurbsSurface.CreateThroughPoints(pts, numOfCellsInY, numOfCellsInX, uDegree, vDegree, uClosed, vClosed)
    terrainBrep = terrainSurface.ToBrep()
    
    
    # project origin_0_0_0 (locationPt) to terrainMesh
    safeHeightDummy = 10000/unitConversionFactor2  # in meters
    origin_0_0_0 = Rhino.Geometry.Point3d(0,0,0)  # always center the terrainMesh to 0,0,0 point
    elevatedOrigin = Rhino.Geometry.Point3d(origin_0_0_0.X, origin_0_0_0.Y, (origin_0_0_0.Z+safeHeightDummy)*scaleFactor)  # project origin_0_0_0 to terrainMesh
    ray = Rhino.Geometry.Ray3d(elevatedOrigin, Rhino.Geometry.Vector3d(0,0,-1))
    rayIntersectParam = Rhino.Geometry.Intersect.Intersection.MeshRay(terrainMesh, ray)
    locationPt = ray.PointAt(rayIntersectParam)
    
    elevationM = locationPt.Z/scaleFactor  # in rhino document units (not meters)
    elevationM = round(elevationM,2)
    
    
    # deleting
    #os.remove(rasterFilePath)  # downloaded .tif file
    os.remove(rasterReprojectedFilePath)  # reprojected .tif file
    del pts
    gc.collect()
    
    return terrainMesh, terrainBrep, locationPt, elevationM


def colorMesh(terrainMesh):
    
    # color the "terrain" mesh
    terrainMesh_numOfVertices = list(terrainMesh.Vertices)
    terrainMesh_verticesZ = [pt.Z for pt in terrainMesh_numOfVertices]
    
    #Gismo legendBakePar_ input (tree)
    legendStyle, legendPlane, maxValue, minValue, customColors, numLegendCells, font, fontSize, numDecimals, legendUnit, customTitle, scale, layerName, layerColor, layerCategoryName = gismo_preparation.read_legendBakePar(legendBakePar_)
    
    colors = gismo_preparation.numberToColor(terrainMesh_verticesZ, customColors)
    #colors = lb_visualization.gradientColor(terrainMesh_verticesZ, lowB, highB, customColors)
    
    terrainMesh.VertexColors.Clear()
    for i in range(len(terrainMesh_numOfVertices)):
        terrainMesh.VertexColors.Add(colors[i])
    
    return terrainMesh  # colored mesh


def split_createStand_colorTerrain(terrainMesh, terrainBrep, locationPt, origin, standThickness, unitConversionFactor2):
    
    scaleFactor = 0.01  # scale terrainMesh 100 times (should never be changed), meaning 1 meter in real life is 0.01 meters in Rhino document
    
    #if (radius_ < (200/unitConversionFactor2)):
    if (radius_ < 200):
        # always reduce the cutting "radius_" unless radius_ is < 200
        cuttingRadiusScaled = radius_ / unitConversionFactor2 * scaleFactor
    else:
        cuttingRadiusScaled = (radius_*0.9) / unitConversionFactor2 * scaleFactor  # 0.9 to avoid the cutting sphere getting out of the terrainMesh/terrainBrep edges
    
    # always perform the cutting of either a mesh or surface regardless if type_ is 0,1,2,3
    if (_type == 0) or (_type == 1):
        # splitting of mesh
        if (_type == 0):
           # split with a cuboid
            boxInterval = Rhino.Geometry.Interval(-cuttingRadiusScaled, cuttingRadiusScaled)
            boxIntervalZ = Rhino.Geometry.Interval(-cuttingRadiusScaled*8, cuttingRadiusScaled*8)  # always use "8"
            boxBrep = Rhino.Geometry.Box(Rhino.Geometry.Plane(locationPt, Rhino.Geometry.Vector3d(0,0,1)), boxInterval, boxInterval, boxIntervalZ).ToBrep()
            boxMeshes = Rhino.Geometry.Mesh.CreateFromBrep(boxBrep)
            boxMesh = Rhino.Geometry.Mesh();
            for mesh in boxMeshes:
                boxMesh.Append(mesh)
            terrainMeshesSplitted = terrainMesh.Split(boxMesh)
        
        elif (_type == 1):
            # split with a sphere
            meshSphere = Rhino.Geometry.Mesh.CreateFromSphere(Rhino.Geometry.Sphere(locationPt, cuttingRadiusScaled), 48, 40)
            terrainMeshesSplitted = terrainMesh.Split(meshSphere)
    
    
    elif (_type == 2) or (_type == 3):
        # splitting of surface
        if (_type == 2):
            # split with a cuboid
            boxInterval = Rhino.Geometry.Interval(-cuttingRadiusScaled, cuttingRadiusScaled)
            boxIntervalZ = Rhino.Geometry.Interval(-cuttingRadiusScaled*5, cuttingRadiusScaled*5)  # always use "5"
            boxBrep = Rhino.Geometry.Box(Rhino.Geometry.Plane(locationPt, Rhino.Geometry.Vector3d(0,0,1)), boxInterval, boxInterval, boxIntervalZ).ToBrep()
            terrainBrepsSplitted = terrainBrep.Split(boxBrep, 0.01)
        
        elif (_type == 3):
            # split with a sphere
            brepSphere = Rhino.Geometry.Sphere(locationPt, cuttingRadiusScaled).ToBrep()
            terrainBrepsSplitted = terrainBrep.Split(brepSphere, 0.01)
        
        [splittedBrep.Faces.ShrinkFaces() for splittedBrep in terrainBrepsSplitted]
        terrainMeshesSplitted = [Rhino.Geometry.Mesh.CreateFromBrep(splittedBrep) for splittedBrep in terrainBrepsSplitted]  # convert terrainBrepsSplitted to meshes for quicker calculation
    
    
    tupleDistanceToLocationPt = [ (Rhino.Geometry.AreaMassProperties.Compute(splittedMesh).Centroid .DistanceTo(locationPt),  i)  for i,splittedMesh in enumerate(terrainMeshesSplitted)]  # calculate the distance from centroids of the meshes from terrainMeshesSplitted to locationPt
    tupleDistanceToLocationPt.sort()
    
    if (_type == 0) or (_type == 1):
        terrain_MeshOrBrep_Splitted = terrainMeshesSplitted[tupleDistanceToLocationPt[0][1]]
        terrainOutlines = [polyline.ToNurbsCurve() for polyline in terrain_MeshOrBrep_Splitted.GetNakedEdges()]
    elif (_type == 2) or (_type == 3):
        terrain_MeshOrBrep_Splitted = terrainBrepsSplitted[tupleDistanceToLocationPt[0][1]]
        nakedOnly = True
        terrainOutlines = terrain_MeshOrBrep_Splitted.DuplicateEdgeCurves(nakedOnly)
    
    
    
    # stand
    standThickness = standThickness/100  # due to scalling of the terrain_Mesh_colored 100 times
    if (standThickness == 0):
        # stand should not be created
        if (_type == 0) or (_type == 1):
            # just color the mesh
            terrain_Mesh_colored = colorMesh(terrain_MeshOrBrep_Splitted)
            del terrainBrep
            
            return terrain_Mesh_colored
        elif (_type == 2) or (_type == 3):
            del terrainMesh
            
            return terrain_MeshOrBrep_Splitted
    
    elif (standThickness > 0):
        # create stand
        accurate = True
        terrainBB = terrain_MeshOrBrep_Splitted.GetBoundingBox(accurate)
        lowestZcoordinatePt = terrainBB.Min  # point with the lowest Z coordinate
        terrainLowestVertexPlane = Rhino.Geometry.Plane(lowestZcoordinatePt, Rhino.Geometry.Vector3d(0,0,1))
        terrainLowestVertexPlane2 = Rhino.Geometry.Plane(terrainLowestVertexPlane.Origin, Rhino.Geometry.Vector3d(0,0,1))
        terrainLowestVertexPlane.Origin = Rhino.Geometry.Point3d(terrainLowestVertexPlane.Origin.X, terrainLowestVertexPlane.Origin.Y, terrainLowestVertexPlane.Origin.Z - standThickness)
        
        terrainOutline = Rhino.Geometry.Curve.JoinCurves(terrainOutlines)[0]
        terrainOutlineProjected = Rhino.Geometry.Curve.ProjectToPlane(terrainOutline, terrainLowestVertexPlane)  # "terrainOutline" projected to the "terrainLowestVertexPlane" plane
        
        loftType = Rhino.Geometry.LoftType.Straight; closedLoft = False
        loftedTerrain_Outline_and_OutlineProjected_Brep = Rhino.Geometry.Brep.CreateFromLoft([terrainOutline, terrainOutlineProjected], Rhino.Geometry.Point3d.Unset, Rhino.Geometry.Point3d.Unset, loftType, closedLoft)[0]
        
        terrainOutlineProjected_Brep = Rhino.Geometry.Brep.CreatePlanarBreps([terrainOutlineProjected])[0]
        loftedTerrain_Outline_and_OutlineProjected_Brep__and__terrainOutlineProjected_Brep = Rhino.Geometry.Brep.JoinBreps([loftedTerrain_Outline_and_OutlineProjected_Brep, terrainOutlineProjected_Brep],0.001)[0]
        
        
        if (_type == 2) or (_type == 3):
            # surface, no coloring should be performed
            loftedTerrain_Outline_and_OutlineProjected_Brep__and__terrainOutlineProjected_Brep__and__terrain = Rhino.Geometry.Brep.JoinBreps([terrain_MeshOrBrep_Splitted, loftedTerrain_Outline_and_OutlineProjected_Brep, terrainOutlineProjected_Brep],0.001)[0]
            del terrainMesh
            
            return loftedTerrain_Outline_and_OutlineProjected_Brep__and__terrainOutlineProjected_Brep__and__terrain
        elif (_type == 0) or (_type == 1):
            # mesh, color the meshes
            meshParam = Rhino.Geometry.MeshingParameters()
            # setting the meshParam so that it does not crash Rhino
            if (radius_ <= 300):
                meshParam.MaximumEdgeLength = 0.1
            elif (radius_ > 300) and (radius_ <= 400):
                meshParam.MaximumEdgeLength = 0.2
            elif (radius_ > 400) and (radius_ <= 500):
                meshParam.MaximumEdgeLength = 0.3
            elif (radius_ > 500) and (radius_ <= 1000):
                meshParam.MaximumEdgeLength = 0.4
            elif (radius_ > 1000) and (radius_ <= 2000):
                meshParam.MaximumEdgeLength = 0.5
            elif (radius_ > 2000) and (radius_ <= 3000):
                meshParam.MaximumEdgeLength = 0.7
            elif (radius_ > 3000) and (radius_ <= 4000):
                meshParam.MaximumEdgeLength = 0.9
            elif (radius_ > 4000):
                meshParam.MaximumEdgeLength = 10
            
            loftedTerrain_Outline_and_OutlineProjected_Brep__and__terrainOutlineProjected_Brep_Mesh = Rhino.Geometry.Mesh.CreateFromBrep(loftedTerrain_Outline_and_OutlineProjected_Brep__and__terrainOutlineProjected_Brep, meshParam)  # it can contain more than one mesh
            terrain_withStand = Rhino.Geometry.Mesh()  # for scaling of terrainShadingMask
            for meshMaskPart in loftedTerrain_Outline_and_OutlineProjected_Brep__and__terrainOutlineProjected_Brep_Mesh:
                terrain_withStand.Append(meshMaskPart)
            terrain_withStand.Append(terrain_MeshOrBrep_Splitted)
            
            terrain_withStand_colored = colorMesh(terrain_withStand)
            del terrainBrep
            
            return terrain_withStand_colored


def createElevationContours(terrainUnoriginUnscaledUnrotated, numOfContours, _type):
    
    # create intersection planes
    accurate = True
    terrainBB_edges = terrainUnoriginUnscaledUnrotated.GetBoundingBox(accurate).GetEdges()
    terrainBB_verticalEdge = terrainBB_edges[8]  # "Rhino.Geometry.Line" type
    includeEnds = False
    terrainBB_edges_t_parameters = terrainBB_verticalEdge.ToNurbsCurve().DivideByCount(numOfContours, includeEnds)
    elevationContours_planeOrigins = [Rhino.Geometry.Line.PointAt(terrainBB_verticalEdge, t)  for t in terrainBB_edges_t_parameters]
    elevationContours_planes = [Rhino.Geometry.Plane(origin, Rhino.Geometry.Vector3d(0,0,1))  for origin in elevationContours_planeOrigins]
    
    if (_type == 0) or (_type == 1):
        elevationContours_Polylines = list(Rhino.Geometry.Intersect.Intersection.MeshPlane(terrainUnoriginUnscaledUnrotated, elevationContours_planes))
        elevationContours = [crv.ToNurbsCurve()  for crv in elevationContours_Polylines]  # curves
    elif (_type == 2) or (_type == 3):
        elevationContours = []
        for plane in elevationContours_planes:
            success, elevationContoursSubList, elevationContourPointsSubList = Rhino.Geometry.Intersect.Intersection.BrepPlane(terrainUnoriginUnscaledUnrotated, plane, 0.01)
            #elevationContoursSubList_closedCrvs = [crv  for crv in elevationContoursSubList  if crv.IsClosed] # remove elevationContours crvs which are not closed
            elevationContoursSubList_closedCrvs = [crv  for crv in elevationContoursSubList]
            if len(elevationContoursSubList_closedCrvs) > 0:  # or success == True
                elevationContours.extend(elevationContoursSubList_closedCrvs)
    
    return elevationContours


def title_scalingRotating(terrainUnoriginUnscaledUnrotated, locationName, locationLatitudeD, locationLongitudeD, locationPt, maxVisibilityRadiusM, _type, origin, northDeg, northRad, numOfContours, unitConversionFactor):
    
    # scaling, rotating
    originTransformMatrix = Rhino.Geometry.Transform.PlaneToPlane(  Rhino.Geometry.Plane(locationPt, Rhino.Geometry.Vector3d(0,0,1)), Rhino.Geometry.Plane(origin, Rhino.Geometry.Vector3d(0,0,1)) )  # move the terrain from "locationPt" to "origin"
    scaleTransformMatrix = Rhino.Geometry.Transform.Scale( Rhino.Geometry.Plane(origin, Rhino.Geometry.Vector3d(0,0,1)), 100, 100, 100 )  # scale the whole terrain back to its real size due to previous usage of scaleFactor = 0.01
    # rotation due to north angle position
    #transformMatrixRotate = Rhino.Geometry.Transform.Rotation(-northRad, Rhino.Geometry.Vector3d(0,0,1), origin)  # counter-clockwise
    rotateTransformMatrix = Rhino.Geometry.Transform.Rotation(northRad, Rhino.Geometry.Vector3d(0,0,1), origin)  # clockwise
    
    if numOfContours_ > 0:
        # create elevationContours
        elevationContours_UnoriginUnscaledUnrotated = createElevationContours(terrainUnoriginUnscaledUnrotated, numOfContours, _type)
    else:
        # no elevationContours will be created
        elevationContours_UnoriginUnscaledUnrotated = []
    geometry = [terrainUnoriginUnscaledUnrotated] + elevationContours_UnoriginUnscaledUnrotated
    for g in geometry:
        if g != None:  # exclude the elevationContours which are invalid (equal to None)
            g.Transform(originTransformMatrix)
            g.Transform(scaleTransformMatrix)
            g.Transform(rotateTransformMatrix)
    
    
    # title
    legendStyle, legendPlane, maxValue, minValue, customColors, numLegendCells, font, fontSize, numDecimals, legendUnit, customTitle, scale, layerName, layerColor, layerCategoryName = gismo_preparation.read_legendBakePar(legendBakePar_)
    
    if (customTitle == None):
        titleLabelText = "Location: %s\nLatitude: %s, Longitude: %s\nRadius: %sm, North: %s" % (locationName, locationLatitudeD, locationLongitudeD, maxVisibilityRadiusM, northDeg)
    else:
        titleLabelText = customTitle
    titleLabelMesh, titleStartPt, titleTextSize = gismo_preparation.createTitle("mesh", [terrainUnoriginUnscaledUnrotated], [titleLabelText], customTitle, textStartPt=None, textSize=fontSize, fontName=font)
    
    
    # hide "origin" output
    ghenv.Component.Params.Output[3].Hidden = True
    
    return terrainUnoriginUnscaledUnrotated, titleLabelMesh, elevationContours_UnoriginUnscaledUnrotated


def bakingGrouping(locationName, locationLatitudeD, locationLongitudeD, maxVisibilityRadiusM, sourceLabel, typeLabel, standThickness, terrain, title, elevationContours, origin):
    
    # baking
    layerName = locationName + "_" + str(locationLatitudeD) + "_" + str(locationLongitudeD) + "_RADIUS=" + str(maxVisibilityRadiusM) + "M" + "_STAND=" + str(round(standThickness,2)) + "_" + sourceLabel + "_" + typeLabel
    
    layParentName = "GISMO"; laySubName = "TERRAIN"; layerCategoryName = "TERRAIN_GENERATOR"
    newLayerCategory = False
    laySubName_color = System.Drawing.Color.FromArgb(100,191,70)  # green
    layerColor = System.Drawing.Color.FromArgb(0,0,0)  # black
    
    layerIndex, layerName_dummy = gismo_preparation.createLayer(layParentName, laySubName, layerCategoryName, newLayerCategory, layerName, laySubName_color, layerColor, legendBakePar_) 
    
    geometryToBakeL = [terrain, title, Rhino.Geometry.Point(origin)]
    geometryIds = gismo_preparation.bakeGeometry(geometryToBakeL, layerIndex)
    
    geometryToBakeL2 = elevationContours
    geometryIds2 = gismo_preparation.bakeGeometry(geometryToBakeL2, layerIndex)
    
    # grouping
    groupIndex = gismo_preparation.groupGeometry(layerName + "_terrainGenerator_elevationContours", geometryIds)
    groupIndex2 = gismo_preparation.groupGeometry(layerName + "_terrainGenerator", geometryIds2)


def printOutput(northDeg, latitude, longitude, locationName, maxVisibilityRadiusM, gridSize, source, sourceLabel, _type, typeLabel, origin, workingSubFolderPath, standThickness, numOfContours):
    if bakeIt_ == True:
        bakedOrNot = "and baked "
    elif bakeIt_ == False:
        bakedOrNot = ""
    resultsCompletedMsg = "Terrain generator component results successfully completed %s!" % bakedOrNot
    printOutputMsg = \
    """
Input data:

Location (deg.): %s
Latitude (deg.): %s
Longitude (deg.): %s
North (deg.): %s

Radius (m): %s
Type: %s (%s)
Origin: %s
Stand thickness (rhino doc. units): %s
Number of elevation contours: %s

Working folder: %s
    """ % (locationName, latitude, longitude, northDeg, maxVisibilityRadiusM, _type, typeLabel, origin, standThickness, numOfContours, workingSubFolderPath)
    print resultsCompletedMsg
    print printOutputMsg


level = Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning
if sc.sticky.has_key("gismoGismo_released"):
    validVersionDate, printMsg = sc.sticky["gismo_check"].versionDate(ghenv.Component)
    if validVersionDate:
        gismo_mainComponent = sc.sticky["gismo_mainComponent"]()
        gismo_preparation = sc.sticky["gismo_Preparation"]()
        gismo_geometry = sc.sticky["gismo_CreateGeometry"]()
        gismo_osm = sc.sticky["gismo_OSM"]()
        
        locationName, locationLatitudeD, locationLongitudeD, timeZone, elevation, validLocationData, printMsg = gismo_preparation.checkLocationData(_location)
        if validLocationData:
            fileNameIncomplete = locationName + "_" + str(locationLatitudeD) + "_" + str(locationLongitudeD) + "_TERRAIN_MASK"  # incomplete due to missing "_visibility=100KM_sph" part (for example)
            heightM = 0; minVisibilityRadiusM = 0; maskStyle = 0; maskStyleLabel = "sph"; downloadUrl_ = None; downloadTSVLink = None;   gridSize_ = 10; source_ = 0  # dummy values
            maxVisibilityRadiusM, gridSize, source, sourceLabel, _type, typeLabel, origin, northRad, northDeg, standThickness, numOfContours, workingSubFolderPath, downloadTSVLink, unitConversionFactor, unitConversionFactor2, validInputData, printMsg = checkInputData(radius_, gridSize_, source_, type_, origin_, north_, standThickness_, numOfContours_, downloadTSVLink)
            if validInputData:
                if _runIt:
                    terrainShadingMaskUnscaledUnrotated, origin_0_0_0, fileName, objFilePath, rasterFilePath, rasterReprojectedFilePath, rasterReprojectedFileNamePlusExtension, vrtFilePath, elevationM, valid_Obj_or_Raster_file, printMsg = checkObjRasterFile(fileNameIncomplete, workingSubFolderPath, downloadTSVLink, heightM, minVisibilityRadiusM, maxVisibilityRadiusM, maskStyleLabel)
                    if valid_Obj_or_Raster_file:
                        if (rasterFilePath != "needless") and (rasterFilePath != "download failed"):  # terrain shading mask NEEDS to be created
                            terrainMesh, terrainBrep, locationPt, elevationM = createTerrainMeshBrep(rasterFilePath, rasterReprojectedFilePath, locationLatitudeD, locationLongitudeD, maxVisibilityRadiusM, unitConversionFactor2)
                            terrainUnoriginUnscaledUnrotated = split_createStand_colorTerrain(terrainMesh, terrainBrep, locationPt, origin, standThickness, unitConversionFactor2)
                        terrain, title, elevationContours = title_scalingRotating(terrainUnoriginUnscaledUnrotated, locationName, locationLatitudeD, locationLongitudeD, locationPt, maxVisibilityRadiusM, _type, origin, northDeg, northRad, numOfContours, unitConversionFactor)
                        if bakeIt_: bakingGrouping(locationName, locationLatitudeD, locationLongitudeD, maxVisibilityRadiusM, sourceLabel, typeLabel, standThickness, terrain, title, elevationContours, origin)
                        printOutput(northDeg, locationLatitudeD, locationLongitudeD, locationName, maxVisibilityRadiusM, gridSize, source, sourceLabel, _type, typeLabel, origin, workingSubFolderPath, standThickness, numOfContours)
                        elevation = elevationM
                    else:
                        print printMsg
                        ghenv.Component.AddRuntimeMessage(level, printMsg)
                else:
                    print "All inputs are ok. Please set \"_runIt\" to True, in order to run the Terrain Generator component"
            else:
                print printMsg
                ghenv.Component.AddRuntimeMessage(level, printMsg)
        else:
            print printMsg
            ghenv.Component.AddRuntimeMessage(level, printMsg)
    else:
        print printMsg
        ghenv.Component.AddRuntimeMessage(level, printMsg)
else:
    printMsg = "First please run the Gismo Gismo component."
    print printMsg
    ghenv.Component.AddRuntimeMessage(level, printMsg)
