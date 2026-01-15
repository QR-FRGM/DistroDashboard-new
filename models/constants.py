"""
Business constants for DistroDashboard.
Moved from core/event_filters.py.
"""

# =============================================================================
# Event Constants
# =============================================================================

EVENTS = ['CPI', 'PPI', 'PCE Price Index', 'Non Farm Payrolls', 'ISM Manufacturing PMI', 'ISM Services PMI',
          'S&P Global Manufacturing PMI Final', 'S&P Global Services PMI Final', 'Michigan',
          'Jobless Claims' , 'ADP' , 'JOLTs' , 'Challenger Job Cuts' , 'Fed Interest Rate Decision' , 
          'GDP Price Index QoQ Adv' , 'Retail Sales' , 'Fed Press Conference', 'FOMC Minutes' ,'Fed Speeches' , 'Month End',
          '2-Year Note Auction' , '3-Year Note Auction' , '5-Year Note Auction' , '7-Year Note Auction' , '10-Year Note Auction' ,
          '20-Year Bond Auction' , '30-Year Bond Auction', 'NY Empire State Manufacturing Index']

#except fed speeches, sub-events for other events come out at the same time. Code is written with this in mind.
SUB_EVENT_DICT = {
    "CPI": ['Inflation Rate MoM' , 'Inflation Rate YoY' , 'Core Inflation Rate MoM' , 'Core Inflation Rate YoY' , 'CPI' , 'CPI s.a'],
    "PPI": ['Core PPI MoM' , 'Core PPI YoY' , 'PPI MoM' , 'PPI YoY'],
    "PCE Price Index": ['Core PCE Prices QoQ' , 'PCE Prices QoQ' , 'PCE Price Index MoM' , 'PCE Price Index YoY' , 'Core PCE Price Index MoM' , 'Core PCE Price Index YoY'],
    "Non Farm Payrolls": ['Non Farm Payrolls' , 'Unemployment Rate' , 'Average Hourly Earnings MoM' , 'Average Weekly Hours' , 'Government Payrolls' , 'Manufacturing Payrolls' , 'Nonfarm Payrolls Private' , 'Participation Rate'],
    "ISM Manufacturing PMI": ['ISM Manufacturing PMI' , 'ISM Manufacturing New Orders' , 'ISM Manufacturing Employment'],
    "ISM Services PMI": ['ISM Services PMI' , 'ISM Services New Orders' , 'ISM Services Employment' , 'ISM Services Business Activity' , 'ISM Services Prices'],
    'S&P Global Manufacturing PMI Final': ['S&P Global Manufacturing PMI Final'], 
    'S&P Global Services PMI Final': ['S&P Global Services PMI Final'],
    'Michigan': ['Michigan Consumer Sentiment Final' , 'Michigan Consumer Sentiment Prel'],
    'Jobless Claims': ['Initial Jobless Claims' , 'Continuing Jobless Claims' , 'Jobless Claims 4-week Average'], 
    'ADP': ['ADP Employment Change'], 
    'JOLTs': ['JOLTs Job Openings' , 'JOLTs Job Quits'], 
    'Challenger Job Cuts': ['Challenger Job Cuts'], 
    'Fed Interest Rate Decision': ['Fed Interest Rate Decision'] , 
    'GDP Price Index QoQ Adv': ['GDP Price Index QoQ Adv' , 'GDP Growth Rate QoQ Adv'] , 
    'Retail Sales': ['Retail Sales MoM' , 'Retail Sales YoY' , 'Retail Sales Ex Autos MoM'] , 
    'Fed Press Conference': ['Fed Press Conference'], 
    'FOMC Minutes': ['FOMC Minutes'],
    'Fed Speeches': ['Fed Goolsbee Speech' , 'Fed Kashkari Speech' , 'Fed Waller Speech' , 'Fed Bostic Speech' , 'Fed Kugler Speech',
                     'Fed Collins Speech' , 'Fed Bowman Speech' , 'Fed Barkin Speech' , 'Fed Barr Speech' ,'Fed Daly Speech' , 'Fed Cook Speech',
                     'Fed Harker Speech' , 'Fed Williams Speech' , 'Fed Mester Speech' , 'Fed Musalem Speech' , 'Fed Chair Powell Speech' , 'Fed Jefferson Speech',
                     'Fed Logan Speech' , 'Fed Schmid Speech' , 'Fed Hammack Speech'],
    '2-Year Note Auction': ['2-Year Note Auction'], 
    '3-Year Note Auction': ['3-Year Note Auction'], 
    '5-Year Note Auction': ['5-Year Note Auction'], 
    '7-Year Note Auction': ['7-Year Note Auction'], 
    '10-Year Note Auction': ['10-Year Note Auction'],
    '20-Year Bond Auction': ['20-Year Bond Auction'], 
    '30-Year Bond Auction': ['30-Year Bond Auction'],
    'NY Empire State Manufacturing Index': ['NY Empire State Manufacturing Index']
}

# events that have data as %. Needed later for sub-event filtering
PERCENTAGE_EVENTS = ['Inflation Rate MoM' , 'Inflation Rate YoY' , 'Core Inflation Rate MoM' , 'Core Inflation Rate YoY' , 
                     'Core PPI MoM' , 'Core PPI YoY' , 'PPI MoM' , 'PPI YoY' , 
                     'Core PCE Prices QoQ' , 'PCE Prices QoQ' , 'PCE Price Index MoM' , 'PCE Price Index YoY' , 'Core PCE Price Index MoM' , 'Core PCE Price Index YoY',
                     'Unemployment Rate' , 'Average Hourly Earnings MoM' , 'Participation Rate' , 
                     'Fed Interest Rate Decision' , 
                     'GDP Price Index QoQ Adv' , 'GDP Growth Rate QoQ Adv' ,
                     'Retail Sales MoM' , 'Retail Sales YoY' , 'Retail Sales Ex Autos MoM']

NON_ECO_EVENT_TAGS = ['Market Shift', "Geo", 'Tariff', 'Positioning', 'Election']


