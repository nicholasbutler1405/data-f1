# basic idea: get information for different characteristics for each driver
# 
# create dashboard to show the information
# for each driver, show skill ratings for
#   qualifying pace
#   race pace
#   experience
#   consistency?
#   wet weather
#
# show general statistics like
#   championships
#   wins
#   podiums
#   points
# 
# show something to do with performance around
#   street circuits
#   high-speed
#   mid-speed
#   low-speed

import fastf1
import pandas as pd
from datetime import datetime
import requests
import re
from bs4 import BeautifulSoup
import math
import time

def getDrivers(year):
    url = f"https://api.jolpi.ca/ergast/f1/{year}/drivers/?format=json"
    #print(url)
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        driversData = data['MRData']['DriverTable']['Drivers']
        #print(driversData)
        driversList = []
        for driver in driversData:
            driverInfo = {
                'driverId': driver['driverId'],
                'driverNumber': driver.get('permanentNumber', 'N/A'),
                'code': driver.get('code', 'N/A'),
                'firstName': driver['givenName'],
                'lastName': driver['familyName'],
                'dateOfBirth': driver['dateOfBirth'],
                'nationality': driver['nationality'],
                'url': driver['url']
            }
            driversList.append(driverInfo)
            
        df = pd.DataFrame(driversList)
        
        df['driverId'] = df['driverId'].astype(str)
        df['firstName'] = df['firstName'].astype(str)
        df['lastName'] = df['lastName'].astype(str)
        df['nationality'] = df['nationality'].astype(str)
        df['url'] = df['url'].astype(str)
        df['code'] = df['code'].astype(str)
        
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching drivers: {e}")
        return pd.DataFrame()
    except KeyError as e:
        print(f"Error parsing response: {e}")
        return pd.DataFrame()
    
def getCareerStats(url):
    time.sleep(1)
    import urllib.parse
    pageTitle = url.split('/wiki/')[-1]
    pageTitle = urllib.parse.unquote(pageTitle)
    
    wikiApiUrl = f"https://en.wikipedia.org/w/api.php"
    
    params = {
        'action': 'parse',
        'format': 'json',
        'page': pageTitle,
        'prop': 'text',
        'redirects': True
    }
    
    headers = {
        'User-Agent': 'F1DriverStats/1.0 (nb622@kent.ac.uk)'
    }
    
    try:
        response = requests.get(wikiApiUrl, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        htmlContent = data.get('parse', {}).get('text', {}).get('*', '')
        if not htmlContent:
            print(f"htmlContent not found for {pageTitle}")
            #print(f"API response: {data}")
            return pd.DataFrame({'Championships': [0], 'Wins': [0], 'Podiums': [0], 'Points': [0], 'Entries': [0]})
        
        stats = {
            'Championships': 0,
            'Wins': 0,
            'Podiums': 0,
            'Points': 0,
            'Entries': 0
        }
        
        soup = BeautifulSoup(htmlContent, 'html.parser')
        
        infobox = soup.find('table', class_='infobox')
        if not infobox:
            return pd.DataFrame([stats])
        
        foundStats = {'Championships': False, 'Wins': False, 'Podiums': False, 'Points': False, 'Entries': False}
        
        rows = infobox.find_all('tr')
        for row in rows:
            th = row.find('th')
            td = row.find('td')
            
            if th and td:
                header = th.get_text(strip=True).lower()
                valueText = td.get_text(strip=True)
                
                numbers = re.findall(r'(\d+(?:,\d+)*(?:\.\d+)?)', valueText)
                if numbers:
                    cleanValue = numbers[0].replace(',', '')
                    
                    if 'championships' in header and not foundStats['Championships']:
                        stats['Championships'] = int(float(cleanValue))
                        foundStats['Championships'] = True
                    elif 'wins' in header and not foundStats['Wins']:
                        stats['Wins'] = int(float(cleanValue))
                        foundStats['Wins'] = True
                    elif 'podiums' in header and not foundStats['Podiums']:
                        stats['Podiums'] = int(float(cleanValue))
                        foundStats['Podiums'] = True
                    elif 'points' in header and not foundStats['Points']:
                        stats['Points'] = float(cleanValue)
                        foundStats['Points'] = True
                    elif 'entries' in header and not foundStats['Entries']:
                        stats['Entries'] = int(float(cleanValue))
                        foundStats['Entries'] = True
                        #print(f"driver: {pageTitle}, entries: {stats['Entries']}")
        return pd.DataFrame([stats])
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Wikipedia data: {e}")
        return pd.DataFrame({'Championships': [0], 'Wins': [0], 'Podiums': [0], 'Points': [0], 'Entries': [0]})
    except KeyError as e:
        print(f"Error parsing Wikipedia response: {e}")
        return pd.DataFrame({'Championships': [0], 'Wins': [0], 'Podiums': [0], 'Points': [0], 'Entries': [0]})

def getDriverForm(driverId):
    time.sleep(1)
    url = f"https://api.jolpi.ca/ergast/f1/2025/drivers/{driverId}/results/?format=json"
    print("GETTING ", driverId, " FORM")
    #print(url)
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        racesData = data['MRData']['RaceTable']['Races']
        
        if not racesData:
            print("No race data found")
            return []
                
        resultsList = []
        
        recentRaces = racesData[-5:] if len(racesData) >= 5 else racesData
        
        for race in reversed(recentRaces):
            #print(f"Processing race: {race.get('raceName', 'Unknown')}")
            
            if 'Results' in race and race['Results']:
                result = race['Results'][0]
                
                raceResult = {
                    #'raceName': race['raceName']['Circuit']['Location']['country'],
                    'raceName': race['raceName'],
                    'position': result['position']
                }
                #print(f"Race: {raceResult['raceName']}, Position: {raceResult['position']}")
                resultsList.append(raceResult)
                
        return resultsList
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching driver form: {e}")
        return []
    except KeyError as e:
        print(f"Error parsing response: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []
    
def getDriverStandings():
    allStandings = {}
    
    for roundNum in range(1, 25):
        print(f"Fetching standings for round {roundNum}")
        time.sleep(1)
        url = f"https://api.jolpi.ca/ergast/f1/2025/{roundNum}/driverstandings/?format=json"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if 'StandingsTable' not in data['MRData'] or not data['MRData']['StandingsTable']['StandingsLists']:
                print(f"No standings data for round {roundNum}")
                continue
            
            standingsData = data['MRData']['StandingsTable']['StandingsLists'][0]['DriverStandings']
        
            for index, driver in enumerate(standingsData):
                driverId = driver['Driver']['driverId']                
                position = driver['positionText']
                points = driver['points']
                
                if position == "-":
                    position = index + 1
                
                if driverId not in allStandings.keys():
                    allStandings[driverId] = []
                    
                #print(f"Round {roundNum} - driver: {driverId}, position: {position}")
                
                allStandings[driverId].append(f"{roundNum}&{position}%{points}")
        
        except Exception as e:
            print(f"Unexpected error: {e}")
            continue
        
    return allStandings

def getPerformanceMean(values):
    if len(values) < 4:
        return sum(values) / len(values)
    
    sortedValues = sorted(values)
    
    p1 = len(sortedValues) * 0.1
    p3 = len(sortedValues) * 0.9
    
    start = int(math.ceil(p1))
    end = int(math.floor(p3))
    
    middle = sortedValues[start:end + 1]
    
    return sum(middle) / len(middle)

def getSeasonResults():
    qualifyingScores = {}
    racePaceScores = {}
    allRaceResults = {}
    
    for roundNum in range(1, 25):
        print(f"Fetching qualifying data for round {roundNum}")
        time.sleep(0.5)
        constrUrl = f"https://api.jolpi.ca/ergast/f1/2025/{roundNum}/constructorstandings/?format=json"
        qualiUrl = f"https://api.jolpi.ca/ergast/f1/2025/{roundNum}/qualifying/?format=json"
        raceUrl = f"https://api.jolpi.ca/ergast/f1/2025/{roundNum}/results/?format=json"
        
        try:
            constrResponse = requests.get(constrUrl)
            constrResponse.raise_for_status()
            constrData = constrResponse.json()
            
            time.sleep(0.5)
            
            qualiResponse = requests.get(qualiUrl)
            qualiResponse.raise_for_status()
            qualiData = qualiResponse.json()
            
            time.sleep(0.5)
            
            raceResponse = requests.get(raceUrl)
            raceResponse.raise_for_status()
            raceData = raceResponse.json()
            
            if ('StandingsTable' not in constrData['MRData'] or not constrData['MRData']['StandingsTable']['StandingsLists']):
                print(f"No constructor standings for round {roundNum}")
                continue
            
            if ('RaceTable' not in qualiData['MRData'] or not qualiData['MRData']['RaceTable']['Races']):
                print(f"No qualifying data for round {roundNum}")
                continue
            
            if ('RaceTable' not in raceData['MRData'] or not raceData['MRData']['RaceTable']['Races']):
                print(f"No race results for round {roundNum}")
                continue
            
            constrStandings = constrData['MRData']['StandingsTable']['StandingsLists'][0]['ConstructorStandings']
            constrPositions = {}
            
            for standing in constrStandings:
                constrId = standing['Constructor']['constructorId']
                position = int(standing['position'])
                constrPositions[constrId] = position
                
            raceInfo = raceData['MRData']['RaceTable']['Races'][0]
            raceName = raceInfo['raceName']
            country = raceInfo['Circuit']['Location']['country']
            
            qualiResults = qualiData['MRData']['RaceTable']['Races'][0]['QualifyingResults']
            
            raceResults = raceData['MRData']['RaceTable']['Races'][0]['Results']
            
            for index, result in enumerate(qualiResults):
                driverId = result['Driver']['driverId']
                qualiPos = int(result['position'])
                constrId = result['Constructor']['constructorId']
                
                if qualiPos in ["-", "R", "W", "D"]:
                    qualiPos = str(index + 1)
                
                if constrId not in constrPositions:
                    print(f"Constructor {constrId} not found in standings")
                    continue
                
                constrPos = constrPositions[constrId]
                originalMin = (constrPos * 2) - 1
                originalMax = constrPos * 2
                originalAvg = (originalMin + originalMax) / 2
                
                compression = 0.7
                middle = 5                
                compressedAvg = middle + (originalAvg - middle) * compression                
                expectedAvg = compressedAvg
                performance = expectedAvg - qualiPos
                
                if performance < 0:
                    performance = -(math.pow(abs(performance), 1.2)) / 3
                else:
                    performance = math.pow(performance, 1.2) / 1.5
                
                print(f"Round {roundNum} - {driverId}: Q{qualiPos}, expected P{expectedAvg}, score: {performance:.1f}")
                
                if driverId not in qualifyingScores:
                    qualifyingScores[driverId] = []
                    
                qualifyingScores[driverId].append({
                    'round': roundNum,
                    'qualifyingPos': qualiPos,
                    'performance': performance
                })
                
            for result in raceResults:
                driverId = result['Driver']['driverId']
                racePos = result['positionText']
                constrId = result['Constructor']['constructorId']
                
                if racePos in ["-", "R", "W", "D"]:
                    racePos = str(index + 1)
                    
                for qualiResult in qualiResults:
                    if qualiResult['Driver']['driverId'] == driverId:
                        qualiPos = qualiResult['position']
                        break
                
                if driverId not in allRaceResults:
                    allRaceResults[driverId] = []
                    
                allRaceResults[driverId].append({
                    'country': country,
                    'racePosition': racePos,
                    'qualiPosition': qualiPos,
                    'round': roundNum
                })
                
                if racePos in ["-", "R", "W", "D"]:
                    print(f"Round {roundNum} - {driverId}: DNF/DSQ, skipping")
                    continue
                
                racePos = int(racePos)
                
                if constrId not in constrPositions:
                    continue
                
                constrPos = constrPositions[constrId]
                originalMin = (constrPos * 2) - 1
                originalMax = constrPos * 2
                originalAvg = (originalMin + originalMax) / 2
                
                compression = 0.5
                middle = 5                
                compressedAvg = middle + (originalAvg - middle) * compression
                expectedAvg = compressedAvg
                racePacePerformance = expectedAvg - racePos
                
                if racePacePerformance < 0:
                    racePacePerformance = -(math.pow(abs(racePacePerformance), 1.2)) / 3
                else:
                    racePacePerformance = math.pow(racePacePerformance, 1.2) / 1.5
                
                print(f"Round {roundNum} - {driverId}: Race P{racePos}, expected P{expectedAvg:.1f}, race pace: {racePacePerformance:.1f}")
                
                if driverId not in racePaceScores:
                    racePaceScores[driverId] = []
                    
                racePaceScores[driverId].append({
                    'round': roundNum,
                    'racePos': racePos,
                    'racePacePerformance': racePacePerformance
                })
                    
        except Exception as e:
            print(f"Unexpected error: {e}")
            continue
    
    driverSkillsAvgs = {}    
    allDriverIds = set(list(qualifyingScores.keys()) + list(racePaceScores.keys()))
    
    for driverId in allDriverIds:
        driverSkillsAvgs[driverId] = {}
        
        if driverId in qualifyingScores and qualifyingScores[driverId]:
            performances = [score['performance'] for score in qualifyingScores[driverId]]
            performanceMeanQuali = getPerformanceMean(performances)
            driverSkillsAvgs[driverId]['avgQualifyingPerformance'] = round(performanceMeanQuali, 2)
        else:
            driverSkillsAvgs[driverId]['avgQualifyingPerformance'] = 0
            
        if driverId in racePaceScores and racePaceScores[driverId]:
            performances = [score['racePacePerformance'] for score in racePaceScores[driverId]]
            performanceMeanRace = getPerformanceMean(performances)
            driverSkillsAvgs[driverId]['avgRacePace'] = round(performanceMeanRace, 2)
        else:
            driverSkillsAvgs[driverId]['avgRacePace'] = 0
            
    return driverSkillsAvgs, allRaceResults
    
def getTeams():
    time.sleep(1)
    url = "https://api.jolpi.ca/ergast/f1/2025/last/races/?format=json"
    print("Getting latest race")
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        raceName = data['MRData']['RaceTable']['Races'][0]['raceName']
        
        session = fastf1.get_session(2025, raceName, 'R')
        session.load(laps=False, telemetry=False, weather=False, messages=False)
            
        teams = {}
        results = session.results
            
        for index, driver in results.iterrows():
            driverAbb = driver['Abbreviation']
            teamName = driver['TeamName']
            teamColour = driver['TeamColor']
            
            teams[driverAbb] = {
                'teamName': teamName,
                'teamColour': teamColour
            }
            
        return teams
    
    except Exception as e:
        print(f"Round not available")
    
drivers2025 = getDrivers(2025)

race = fastf1.get_session(2025, 1, 'R')
race.load()
headshotUrls = race.results[['Abbreviation', 'HeadshotUrl']]
colapintoRow = pd.DataFrame({
    'Abbreviation': ['COL'],
    'HeadshotUrl': ['https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/']
})
headshotUrls = pd.concat([headshotUrls, colapintoRow], ignore_index=True)

driverTeams = getTeams()

allStandings = getDriverStandings()
driverSkills, allRaceResults = getSeasonResults()

print("~~~~~ STANDINGS ~~~~~")
print(allStandings)
print("~~~~~~~~ END ~~~~~~~~")

allDrivers = []

for index, row in drivers2025.iterrows():
    birthDate = datetime.strptime(row['dateOfBirth'], '%Y-%m-%d')
    today = datetime.now()
    age = today.year - birthDate.year - ((today.month, today.day) < (birthDate.month, birthDate.day))
    
    driverStats = getCareerStats(row['url'])
    headshot = headshotUrls[headshotUrls['Abbreviation'] == row['code']]
    if headshot['HeadshotUrl'].iloc[0] == None:
        headshot['HeadshotUrl'] == ""
    
    currentDriver = row.to_dict()
    currentDriver['Headshot'] = headshot['HeadshotUrl'].iloc[0]
    currentDriver['Championships'] = driverStats.iloc[0]['Championships']
    currentDriver['Wins'] = driverStats.iloc[0]['Wins']
    currentDriver['Podiums'] = driverStats.iloc[0]['Podiums']
    currentDriver['Points'] = driverStats.iloc[0]['Points']
    currentDriver['Entries'] = driverStats.iloc[0]['Entries']
    #currentDriver['RecentForm'] = getDriverForm(row['driverId'])
    
    if row['driverId'] in allStandings.keys():
        currentDriver['AllPositions'] = allStandings[row['driverId']]
    else:
        currentDriver['AllPositions'] = []
        
    if row['driverId'] in allRaceResults:
        currentDriver['SeasonResults'] = allRaceResults[row['driverId']]
    else:
        currentDriver['SeasonResults'] = []
        
    if row['driverId'] in driverSkills:
        currentDriver['QualifyingPerformance'] = driverSkills[row['driverId']]['avgQualifyingPerformance']
        currentDriver['RacePace'] = driverSkills[row['driverId']]['avgRacePace']
    else:
        currentDriver['QualifyingPerformance'] = 0
        currentDriver['RacePace'] = 0
        
    if row['code'] in driverTeams:
        currentDriver['TeamName'] = driverTeams[row['code']]['teamName']
        currentDriver['TeamColour'] = driverTeams[row['code']]['teamColour']
    else:
        currentDriver['TeamName'] = 'Unknown'
        currentDriver['TeamColour'] = '808080'
        
    print(currentDriver['QualifyingPerformance'])
    print(currentDriver['RacePace'])
    
    allDrivers.append(currentDriver)
    
driversDf = pd.DataFrame(allDrivers)
print(driversDf)
driversDf.to_csv('drivers-2025.csv', index=False)
