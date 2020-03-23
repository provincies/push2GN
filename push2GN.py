#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# ----- GEBRUIKTE SOFTWARE ---------------------------------------------
#
# python-3.7         https://www.python.org/downloads/release/python-376/
#
# externe libraries:
# requests           https://pypi.org/project/requests/
#
# zie ook: https://geonetwork-opensource.org/manuals/2.10.4/eng/developer/xml_services/csw_services.html#transaction
#          https://docs.geoserver.org/latest/en/user/filter/filter_reference.html
#
# ----- GLOBALE VARIABELEN ---------------------------------------------

__doc__      = 'Programma om iso xmls met een request (push) in Geonetwork te plaatsen'
__rights__   = ['GeoCat', 'provincie Noord-Brabant']
__author__   = ['Paul van Genuchten', 'Jan van Sambeek']
__license__  = 'GNU Lesser General Public License, version 3 (LGPL-3.0)'
__date__     = ['12-2019']
__version__  = '1.2'

# ----- IMPORT LIBRARIES -----------------------------------------------

import sys, os, requests, glob, logging, re, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ----- CONFIG CLASS ---------------------------------------------------

class Config:
  """
  Lees config bestand en haal key's op
  Schrijf dictionarie naar config
  """
  def __init__(self, conf_bestand):
    """ ini config object """
    self.conf_bestand = conf_bestand
    self.conf = None

  def get(self, key, default = None):
    """ Lees values uit config bestand """
    if not self.conf: self.load()
    if self.conf and (key in self.conf): return self.conf[key]
    return default

  def get_dict(self, default = None):
    """ Geef de complete dictionarie """
    if not self.conf: self.load()
    if self.conf: return self.conf
    return default

  def set(self, key, value):
    """ Voeg keys en values toe aan config """
    if not self.conf: self.load()
    self.conf[key] = value
    self.save()

  def load(self):
    """
    Laad het config bestand
    Als het niet bestaat maak een lege config
    """
    try: self.conf = eval(open(self.conf_bestand, 'r').read())
    except: self.conf = {}

  def save(self):
    """ Schijf dictionarie naar config bestand """
    open(self.conf_bestand, 'w').write(repr(self.conf))

# ----- BEPERK_LOG_FILE ------------------------------------------------

def beperk_log_file(log_file, max_regels = 400):
  """
  Als een log bestand te groot wordt verwijder dan de eerste regels
  """
  # open de log file
  with open(log_file, 'r') as log_in: log_regels = log_in.readlines()
  # als de log file langer is als het maximum aantal regels
  if len(log_regels) > max_regels:
    # overschrijf de log met het maximum aantal regels
    with open(log_file, 'w') as log_in: log_regels = log_in.writelines(log_regels[-max_regels:])
  return

# ----- ZENDMAIL -------------------------------------------------------

def Zendmail(mail_gegevens, SSL=True):
  """
  Functie Zendmail(mail_gegevens, SSL=False)

  Is een programma om mail met bijlagen te versturen naar één of meerder ontvangers.
  De mail gegevens bestaan uit, een dictionarie met daarin:
  verzender, wachtwoord, alias, ontvangers, cc, bc,  onderwerp, bericht, de smtp_server en eventueel bijlagen.
  Ontvangers, cc, bc en bijlagen zijn lists, alle overige variabelen zijn strings.
  verplicht: verzender, ontvangers, onderwerp, bericht, de smtp_server
  optioneel: wachtwoord, alias, cc, bc, bijlagen
  Afhankelijk van de provider kan een SSL beveiliging meegegeven worden
  door SSL=True of SSL=False bij het oproepen van de functie mee te geven.


  voorbeeld:

  mail_gegevens = {}
  mail_gegevens['verzender']  = 'verzender@gmail.com'
  mail_gegevens['wachtwoord'] = '********'
  mail_gegevens['alias']      = 'alias verzender'
  mail_gegevens['ontvangers'] = ['ontvanger1@gmail.com', 'ontvanger2@gmail.com']
  mail_gegevens['cc']         = ['cc1@gmail.com, 'cc2@gmail.com']
  mail_gegevens['bc']         = ['bc1@gmail.com, 'bc2@gmail.com']
  mail_gegevens['onderwerp']  = 'onderwerp van de mail'
  mail_gegevens['bericht']    = 'bericht van de mail'
  mail_gegevens['smtp_server']= 'smtp.gmail.com'
  mail_gegevens['bijlagen']   = ['bijlage1.pdf', 'bijlage2.jpg']

  Zendmail(mail_gegevens, SSL=True)
  """
  # stel het bericht samen
  message = MIMEMultipart()
  # kijk of er een alias is anders gebruik de verzender
  if 'alias' in mail_gegevens.keys(): message['From'] = mail_gegevens['alias']
  else: message['From'] = mail_gegevens['verzender']
  # voeg de ontvangers toe aan de message
  message['To'] =  ', '.join(mail_gegevens['ontvangers'])
  # voeg de ontvangers toe aan ontvangers
  ontvangers = mail_gegevens['ontvangers']
  # als er cc's zijn voeg die toe
  if 'cc' in mail_gegevens.keys():
    message['CC'] =  ', '.join(mail_gegevens['cc'])
    ontvangers += mail_gegevens['cc']
  # als er bc's zijn voeg die toe
  if 'bc' in mail_gegevens.keys():
    message['BC'] =  ', '.join(mail_gegevens['bc'])
    ontvangers += mail_gegevens['bc']
  # voeg het onderwerp toe
  message['Subject'] = mail_gegevens['onderwerp']
  # voeg het bericht toe
  message.attach(MIMEText(mail_gegevens['bericht'], 'plain'))
  # als er bijlagen zijn voeg ze dan toe
  if 'bijlagen' in mail_gegevens.keys():
    # loop door alle bijlagen
    for mail_best in mail_gegevens['bijlagen']:
      bijlage = MIMEBase('application', "octet-stream")
      bijlage.set_payload(open(mail_best,"rb").read())
      encoders.encode_base64(bijlage)
      bijlage.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(mail_best))
      # voeg de bijlage toe
      message.attach(bijlage)
  # maak een beveiligde of onbeveiligde verbinding met de smtp server
  if SSL: smtp = smtplib.SMTP_SSL(mail_gegevens['smtp_server'])
  else: smtp = smtplib.SMTP(mail_gegevens['smtp_server'])
  # zet het debuglevel op false
  smtp.set_debuglevel(False)
  # login bij de smtp server
  if 'wachtwoord' in mail_gegevens.keys():
    smtp.login(mail_gegevens['verzender'], mail_gegevens['wachtwoord'].decode('base64','strict'))
  # verzend de totale mail
  smtp.sendmail(mail_gegevens['verzender'], ontvangers, message.as_string())
  # stop het object
  smtp.quit()
  return

# ----- VERVANG CONTACT ------------------------------------------------

def vervang_contact(xml, cont_gegevens):
  """
  Vervang de contact gegevens door algemene contact gegevens
  """
  # zoek op MD_DataIdentification
  zoekstring = 'MD_DataIdentification'
  # maak een list van de MD_DataIdentification pointers
  id_pointers = sorted([pointer.start() for pointer in re.finditer(zoekstring, xml)])
  # zoek MD_Distributor
  zoekstring = 'MD_Distributor'
  # maak een list van de MD_Distributor pointers
  dist_pointers = sorted([pointer.start() for pointer in re.finditer(zoekstring, xml)])
  # verwijder de quality contact gegevens
  # bepaal de zoekstring voor de quality contact gegevens met > ivm CI_RoleCode lijst
  zoekstring = 'processor>'
  # maak een list van de begin pointers en sorteer reverse om vanaf achter de contact gegevens te verwijderen
  pointers = sorted([pointer.start() for pointer in re.finditer(zoekstring, xml)], reverse = True)
  # als ze gevuld zijn
  if pointers:
    # loop in stappen van 2 door de pointers
    for num in range(len(pointers))[::2]:
      # bepaal de left pointer
      lpoint = xml[: pointers[num+1]].rfind('<')
      # bepaal de right pointer
      rpoint = pointers[num] + len(zoekstring)
      # verwijder de quality contact gegevens uit de xml
      xml = xml[: lpoint] + xml[rpoint: ]
  # wijzig de overige contact gegevens
  # zoek stings
  zoekstring = 'gmd:CI_ResponsibleParty'
  # als de zoek string bestaat bepaal dan de namespaces
  if xml.find(zoekstring) >= 0:
    ns_gmd = 'gmd:'
    ns_gco = ' xmlns:gco="http://www.isotc211.org/2005/gco"'
  # kijk of de zoekstring zonder namespace bestaat en bepaal de namespaces
  elif xml.find(zoekstring.split(':')[-1]) >= 0:
    ns_gmd = ''
    ns_gco = ''
    zoekstring = zoekstring.split(':')[-1]
  # de zoekstring komt niet voor, verlaat de functie
  else: return xml
  # maak een list van de begin pointers en sorteer reverse om vanaf achter de contact gegevens te vervangen
  pointers = sorted([pointer.start() for pointer in re.finditer(zoekstring, xml)], reverse = True)
  # bepaal de vervang gegevens
  vervangstring = '<%sCI_ResponsibleParty>\n' %(ns_gmd)
  if 'organisatie' in cont_gegevens.keys():
    vervangstring += '<%sorganisationName>\n' %(ns_gmd)
    vervangstring += '<gco:CharacterString%s>%s</gco:CharacterString>\n' %(ns_gco, cont_gegevens['organisatie'])
    vervangstring += '</%sorganisationName>\n' %(ns_gmd)
  vervangstring += '<%scontactInfo>\n' %(ns_gmd)
  vervangstring += '<%sCI_Contact>\n' %(ns_gmd)
  if 'tel' in cont_gegevens.keys():
    vervangstring += '<%sphone>\n' %(ns_gmd)
    vervangstring += '<%sCI_Telephone>\n' %(ns_gmd)
    vervangstring += '<%svoice>\n' %(ns_gmd)
    vervangstring += '<gco:CharacterString%s>%s</gco:CharacterString>\n' %(ns_gco, cont_gegevens['tel'])
    vervangstring += '</%svoice>\n' %(ns_gmd)
    vervangstring += '</%sCI_Telephone>\n' %(ns_gmd)
    vervangstring += '</%sphone>\n' %(ns_gmd)
  vervangstring += '<%saddress>\n' %(ns_gmd)
  vervangstring += '<%sCI_Address>\n' %(ns_gmd)
  if 'adres' in cont_gegevens.keys():
    vervangstring += '<%sdeliveryPoint>\n' %(ns_gmd)
    vervangstring += '<gco:CharacterString>%s</gco:CharacterString>\n' %(ns_gco, cont_gegevens['adres'])
    vervangstring += '</%sdeliveryPoint>\n' %(ns_gmd)
  if 'plaats' in cont_gegevens.keys():
    vervangstring += '<%scity>\n' %(ns_gmd)
    vervangstring += '<gco:CharacterString>%s</gco:CharacterString>\n' %(ns_gco, cont_gegevens['plaats'])
    vervangstring += '</%scity>\n' %(ns_gmd)
  if 'provincie' in cont_gegevens.keys():
    vervangstring += '<%sadministrativeArea>\n' %(ns_gmd)
    vervangstring += '<gco:CharacterString>%s</gco:CharacterString>\n' %(ns_gco, cont_gegevens['provincie'])
    vervangstring += '</%sadministrativeArea>\n' %(ns_gmd)
  if 'postcode' in cont_gegevens.keys():
    vervangstring += '<%spostalCode>\n' %(ns_gmd)
    vervangstring += '<gco:CharacterString>%s</gco:CharacterString>\n' %(ns_gco, cont_gegevens['postcode'])
    vervangstring += '</%spostalCode>\n' %(ns_gmd)
  if 'land' in cont_gegevens.keys():
    vervangstring += '<%scountry>\n' %(ns_gmd)
    vervangstring += '<gco:CharacterString>Nederland</gco:CharacterString>\n' %(ns_gco, cont_gegevens['land'])
    vervangstring += '</%scountry>\n' %(ns_gmd)
  if 'email' in cont_gegevens.keys():
    vervangstring += '<%selectronicMailAddress>\n' %(ns_gmd)
    vervangstring += '<gco:CharacterString%s>%s</gco:CharacterString>\n' %(ns_gco, cont_gegevens['email'])
    vervangstring += '</%selectronicMailAddress>\n' %(ns_gmd)
  vervangstring += '</%sCI_Address>\n' %(ns_gmd)
  vervangstring += '</%saddress>\n' %(ns_gmd)
  if 'url' in cont_gegevens.keys():
    vervangstring += '<%sonlineResource>\n' %(ns_gmd)
    vervangstring += '<%sCI_OnlineResource>\n' %(ns_gmd)
    vervangstring += '<%slinkage>\n' %(ns_gmd)
    vervangstring += '<URL%s>%s</URL>\n' %(ns_gco, cont_gegevens['url'])
    vervangstring += '</%slinkage>\n' %(ns_gmd)
    vervangstring += '</%sCI_OnlineResource>\n' %(ns_gmd)
    vervangstring += '</%sonlineResource>\n' %(ns_gmd)
  vervangstring += '</%sCI_Contact>\n' %(ns_gmd)
  vervangstring += '</%scontactInfo>\n' %(ns_gmd)
  # loop in stappen van 2 door de pointers
  for num in range(len(pointers))[::2]:
    # bepaal de left pointer
    lpoint = xml[: pointers[num+1]].rfind('<')
    # bepaal de right pointer
    rpoint = pointers[num] + xml[pointers[num]: ].find('>') + 1
    # bepaal afhankelijk van de plaats in de xml de CI RoleCode
    RoleCodeString = vervangstring
    RoleCodeString += '<%srole>\n' %(ns_gmd)
    # voor de contacten binnen de MD_DataIdentification tags is de CI RoleCode owner
    if len(id_pointers) > 1 and lpoint > id_pointers[0] and lpoint < id_pointers[1]:
      RoleCodeString += '<%sCI_RoleCode codeList="./resources/codeList.xml#CI_RoleCode" codeListValue="owner" />\n' %(ns_gmd)
    # voor de contacten binnen de MD_DataIdentification tags is de CI RoleCode distibutor
    elif len(dist_pointers) > 1 and lpoint > dist_pointers[0] and lpoint < dist_pointers[1]:
      RoleCodeString += '<%sCI_RoleCode codeList="./resources/codeList.xml#CI_RoleCode" codeListValue="distributor" />\n' %(ns_gmd)
    # voor de overige contacten is de CI RoleCode pointOfContact
    else:
      RoleCodeString += '<%sCI_RoleCode codeList="./resources/codeList.xml#CI_RoleCode" codeListValue="pointOfContact" />\n' %(ns_gmd)
    RoleCodeString += '</%srole>\n' %(ns_gmd)
    RoleCodeString += '</%sCI_ResponsibleParty>' %(ns_gmd)
    # vervang dmv de RoleCodeString
    xml = xml[: lpoint] + RoleCodeString + xml[rpoint: ]
  # verwijder overbodige contacten
  # verwijder overbodige pointOfContacts
  zoekstring = 'pointOfContact'
  if xml.count(zoekstring) > 2:
    # maak een list van de begin pointers en sorteer reverse om overbodige contact gegevens te verwijderen
    pointers = sorted([pointer.start() for pointer in re.finditer(zoekstring, xml)], reverse = True)
    # verwijder de codelistvalues "pointOfContact"
    for pointer in re.finditer('"'+zoekstring+'"', xml):
      if pointer.start()+1 in pointers: pointers.remove(pointer.start()+1)
    # verwijder de laatste 2 pointers (die moeten blijven)
    pointers = pointers[:-2]
    # als pointers niet leeg is verwijder dan de overige pointOfContacts
    if pointers:
      # loop in stappen van 2 door de pointers
      for num in range(len(pointers))[::2]:
        # bepaal de left pointer
        lpoint = xml[: pointers[num+1]].rfind('<')
        # bepaal de right pointer
        rpoint = pointers[num] + xml[pointers[num]: ].find('>') + 1
        # verwijder de overbodige contact gegevens
        xml = xml[: lpoint] + xml[rpoint: ]
  return xml

# ----- RESPONSECOUNT --------------------------------------------------

def responseCount(response, zoekTekst, tags):
  """
  Functie om een nummer terug te geven uit de requests reponse
  met behulp van een zoekstekst en afsluitende quotes/tags:
  """
  # lees de response tekst
  response = response.text
  # bepaal de positie van de linker pointer
  lpoint = response.find(zoekTekst+tags[:1])+len(zoekTekst+tags[:1])
  # bepaal de positie van de rechter pointer
  rpoint = lpoint+response[lpoint:].find(tags[1:])
  # lees de waarde tussen de pointers
  aantalRecords = response[lpoint: rpoint]
  # geef een int terug of een false
  if aantalRecords.isdigit(): return int(aantalRecords)
  else: return False
  
# ----- ZOEK WAARDE ----------------------------------------------------

def zoek_waarde(xml, tags):
  """
  zoek in de xml naar een waarde tussen 2 tags
  """
  # bepaal de linker en rechter pointer
  if xml.find(tags[0]) > 0:
    lpoint = xml.find(tags[0])
    if xml[xml.find(tags[0]):].find(tags[1]) > 0:
      lpoint += xml[xml.find(tags[0]):].find(tags[1])
      lpoint += xml[xml.find(tags[0])+xml[xml.find(tags[0]):].find(tags[1]):].find('>')+1
      rpoint = lpoint + xml[lpoint:].find('<')
      # return waarde
      return xml[lpoint:rpoint]
    else: return False
  else: return False

# ----- HOOFD PROGRAMMA ------------------------------------------------

if __name__ == '__main__':
  """
  Programma om iso xmls in Geonetwork (GN) te plaatsen
  """
  # bepaal de start directorie en bestand
  start_dir, bestand  = os.path.split(os.path.abspath(__file__))
  # maak een object van de configuratie data
  if os.path.isfile(start_dir+os.sep+os.path.splitext(bestand)[0]+'.cfg'):
    cfg = Config(start_dir+os.sep+os.path.splitext(bestand)[0]+'.cfg')
  # verlaat anders het programma
  else: sys.exit('het configuratie bestand is niet gevonden')
  # als het configuratie bestand niet goed is verlaat het programma
  if cfg.get_dict() == None: sys.exit('er is iets niet goed met het configuratie bestand')
  # lees de directories uit
  xml_map = cfg.get('dirs')['MM_dir']
  log_dir = cfg.get('dirs')['log_dir']
  # lees de URL, user en password, etc. uit
  URL = cfg.get('inlog_geg')['URL']
  user = cfg.get('inlog_geg')['user']
  password = cfg.get('inlog_geg')['password']
  orgNaam = cfg.get('orgNaam')
  verifyRequest = cfg.get('verifyRequest')
  # maak een log bestand
  log_file = log_dir+os.sep+os.path.splitext(bestand)[0]+'.log'
  # maak een basis configuratie voor het loggen
  logging.basicConfig(filemode='a', format='%(asctime)s - %(levelname)-8s "%(message)s"', datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO, filename=log_file)
  # het programma is gestart
  logging.info('-'*50)
  logging.info('%s is opgestart' %(__file__))
  logging.info('-'*50)
  # maak een lege list
  fileUuids = []
  # maak lege tellers
  tellers = [0, 0, 0, 0]
  # maak een leeg mail bericht
  mail_bericht = ''
  # maak een lege list voor de huidige GN file uuids en datums
  GNuuidDates = {}
  # open een sessie om een cookie te creeeren
  client = requests.Session() 
  # vul de csw GetRecords tekst 
  cswGetRecords = '<?xml version="1.0" encoding="UTF-8"?>\n'
  cswGetRecords += '<csw:GetRecords xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" '
  cswGetRecords += 'xmlns:ogc="http://www.opengis.net/ogc" '
  cswGetRecords += 'xmlns:dc="http://www.purl.org/dc/elements/1.1/" '
  cswGetRecords += 'version="2.0.2" service="CSW" resultType="results" startPosition="1" maxRecords="20000" '
  cswGetRecords += 'outputSchema="http://www.isotc211.org/2005/gmd" outputFormat="application/xml">\n'
  cswGetRecords += '<csw:Query typeNames="gmd:MD_Metadata">\n'
  cswGetRecords += '<csw:ElementSetName>full</csw:ElementSetName>\n'
  cswGetRecords += '<csw:Constraint version="1.0.0">\n'
  cswGetRecords += '<ogc:Filter>\n'
  cswGetRecords += '<ogc:PropertyIsEqualTo>\n'
  cswGetRecords += '<ogc:PropertyName>dc:OrganisationName</ogc:PropertyName>\n'
  cswGetRecords += '<ogc:Literal>%s</ogc:Literal>\n' %(orgNaam) 
  cswGetRecords += '</ogc:PropertyIsEqualTo>\n'
  cswGetRecords += '</ogc:Filter>\n'
  cswGetRecords += '</csw:Constraint>\n'
  cswGetRecords += '</csw:Query>\n'
  cswGetRecords += '</csw:GetRecords>'
  # lees alle records van de Organisatie uit
  try:
    GetRecords_response = client.post(URL+'/geonetwork/srv/eng/csw', data=cswGetRecords.encode('utf-8'), headers={'Content-Type': 'application/xml'}, auth=(user, password), verify=verifyRequest)
  except requests.exceptions.RequestException as foutje:
    logging.info('Er gaat iets mis bij het uitlezen van GetRecords: %s' %(foutje))
    mail_bericht += 'Er gaat iets mis bij het uitlezen van GetRecords: %s\n' %(foutje) 
  else:
    # vul de dictionary met data
    GNuuidDates.update({zoek_waarde(record, ['fileIdentifier', 'CharacterString']): zoek_waarde(record, ['dateStamp', 'Date']) \
                        for record in GetRecords_response.text.split('MD_Metadata') if zoek_waarde(record, ['fileIdentifier', 'CharacterString'])})    
  #debug# with open(os.path.splitext(bestand)[0]+'_uuids.txt', 'w') as xml:  xml.write(str(GNuuidDates))
  # zet teller 3 op aantal aanwezige records
  tellers[3] = len(GNuuidDates)
  # loop door de map met xml bestanden
  for xmlNaam in glob.glob(xml_map+os.sep+"*xml"):
    # open het bestand als bytes
    with open(xmlNaam, 'rb') as xml: xmlTekst = xml.read().decode('utf-8')
    # start de tekst met <MD_Metadata
    xmlTekst = xmlTekst[xmlTekst.find('<MD_Metadata'):]
    # geef volgend_record een True
    volgend_record = True
    # als er een xml_zoekstring bestaat in het .cfg bestand
    if cfg.get('xml_zoekstring'):
      # geef volgend_record een False
      volgend_record = False
      # als de zoekstrings niet voorkomen in xml ga dan naar de volgende metadata xml
      for zoekstring in cfg.get('xml_zoekstring'):
        # als de zoekstring voorkomt in de xml, zet dan volgend_record op true
        if zoekstring.lower() in xmlTekst.lower(): volgend_record = True
    # als volgend_record niet bestaat ga naar de volgende xml
    if not volgend_record: continue
    # voeg de uuid van het bestand toe aan fileUuids
    fileUuids.append(zoek_waarde(xmlTekst, ['fileIdentifier', 'CharacterString']))
    # lees de wijzigings datum van de metadata uit
    dateStamp = zoek_waarde(xmlTekst, ['dateStamp', 'Date'])
    # als de uuid van het bestand voorkomt in de request uuids
    if zoek_waarde(xmlTekst, ['fileIdentifier', 'CharacterString']) in GNuuidDates.keys():
      # lees de datum uit de GNuuidDates
      GNdate = GNuuidDates[zoek_waarde(xmlTekst, ['fileIdentifier', 'CharacterString'])]
    # geef anders de waarde false (het bestand komt nog niet voor in GN)
    else: GNdate = False
    # als de metadata bestaat in GN en de datum van het bestand is groter als de datum in het GN record
    if GNdate and dateStamp > GNdate:
      # vervang de contact gegevens als de contact gegevens ingevuld zijn in het config bestand
      if cfg.get('cont_gegevens'): xmlTekst = vervang_contact(xmlTekst, cfg.get('cont_gegevens'))
      # voeg csw gegevens toe aan de xmlTekst
      cswUpdate = "<?xml version='1.0' encoding='UTF-8'?>\n"
      cswUpdate += "<csw:Transaction xmlns:csw='http://www.opengis.net/cat/csw/2.0.2' "
      cswUpdate += "xmlns:ogc='http://www.opengis.net/ogc' "
      cswUpdate += "xmlns:dc='http://www.purl.org/dc/elements/1.1/' "
      cswUpdate += "version='2.0.2' service='CSW'>\n"
      cswUpdate += "<csw:Update>\n"
      cswUpdate += xmlTekst
      cswUpdate += "<csw:Constraint version='2.0.0'>\n"
      cswUpdate += "<ogc:Filter>\n"
      cswUpdate += "<ogc:PropertyIsEqualTo>\n"
      cswUpdate += "<ogc:PropertyName>dc:Identifier</ogc:PropertyName>\n"
      cswUpdate += "<ogc:Literal>%s</ogc:Literal>\n" %(zoek_waarde(xmlTekst, ['fileIdentifier', 'CharacterString']))
      cswUpdate += "</ogc:PropertyIsEqualTo>\n"
      cswUpdate += "</ogc:Filter>\n"
      cswUpdate += "</csw:Constraint>\n"
      cswUpdate += "</csw:Update>\n"
      cswUpdate += "</csw:Transaction>\n"
      # vervang de xml in GN
      try:
        response_update = client.post(URL+"/geonetwork/srv/eng/csw-publication", data=cswUpdate.encode('utf-8'), \
                          headers={'Content-Type': 'application/xml'}, auth=(user, password), verify=verifyRequest)
      # exception als er een http foutmelding is https://nl.wikipedia.org/wiki/Lijst_van_HTTP-statuscodes
      except requests.exceptions.ConnectionError as http_foutje: 
        logging.error('Bij het vervangen in GN geeft bestand: %s een http error: %s' %(xmlNaam, http_foutje))
        mail_bericht += 'Bij het vervangen in GN geeft bestand: %s een http error: %s\n' %(xmlNaam, http_foutje) 
        # ga naar de volgende xmlNaam
        continue
      # overige foutmeldingen
      except requests.exceptions.RequestException as foutje: 
        logging.error('Bij het vervangen in GN geeft bestand: %s een fout melding: %s' %(xmlNaam, foutje))
        mail_bericht += 'Bij het vervangen in GN geeft bestand: %s een fout melding: %s\n' %(xmlNaam, foutje) 
        # ga naar de volgende xmlNaam
        continue
      # werk anders de logging, de mail en de teller bij
      else: 
        if responseCount(response_update, 'totalUpdated', '><') == 1:
          logging.info('Bestand: %s is vervangen in Geonetwork' %(xmlNaam))
          mail_bericht += 'Bestand: %s is vervangen in Geonetwork\n' %(xmlNaam)
          tellers[0] += 1
        else:
          logging.info('Bestand: %s is niet vervangen in Geonetwork. Let op!!!' %(xmlNaam))
          mail_bericht += 'Bestand: %s is niet vervangen in Geonetwork. Let op!!!\n' %(xmlNaam)
    # als de GNdate niet bestaat (false), voeg dan de metadata toe aan GN
    elif not GNdate:
      # vervang de contact gegevens als de contact gegevens ingevuld zijn in het config bestand
      if cfg.get('cont_gegevens'): xmlTekst = vervang_contact(xmlTekst, cfg.get('cont_gegevens'))
      # voeg csw gegevens toe aan de xmlTekst
      cswInsert = '<?xml version="1.0" encoding="UTF-8"?>\n'
      cswInsert += '<csw:Transaction service="CSW" version="2.0.2" '
      cswInsert += 'xmlns:csw="http://www.opengis.net/cat/csw/2.0.2">\n'
      cswInsert += '<csw:Insert>\n'
      cswInsert += xmlTekst
      cswInsert += '</csw:Insert>\n'
      cswInsert += '</csw:Transaction>\n'
      # voeg de xml toe aan GN
      try:
        response_insert = client.post(URL+"/geonetwork/srv/eng/csw-publication?publishToAll=true", data=cswInsert.encode('utf-8'), \
                          headers={'Content-Type': 'application/xml'}, auth=(user, password), verify=verifyRequest)
      # exception als er een http foutmelding is https://nl.wikipedia.org/wiki/Lijst_van_HTTP-statuscodes
      except requests.exceptions.ConnectionError as http_foutje: 
        logging.error('Bij het toevoegen in GN geeft bestand: %s een http error: %s' %(xmlNaam, http_foutje))
        mail_bericht += 'Bij het toevoegen in GN geeft bestand: %s een http error: %s\n' %(xmlNaam, http_foutje) 
        # ga naar de volgende xmlNaam
        continue
      # overige foutmeldingen
      except requests.exceptions.RequestException as foutje: 
        logging.error('Bij het toevoegen in GN geeft bestand: %s een fout melding: %s' %(xmlNaam, foutje))
        mail_bericht += 'Bij het toevoegen in GN geeft bestand: %s een fout melding: %s\n' %(xmlNaam, foutje) 
        # ga naar de volgende xmlNaam
        continue
      # werk anders de logging, de mail en de teller bij
      else:
        if responseCount(response_insert, 'totalInserted', '><') == 1:
          logging.info('Bestand: %s is toegevoegd in Geonetwork' %(xmlNaam))
          mail_bericht += 'Bestand: %s is toegevoegd in Geonetwork\n' %(xmlNaam)
          tellers[1] += 1
          tellers[3] += 1
        else:
          logging.info('Bestand: %s is niet toegevoegd in Geonetwork. Let op!!!' %(xmlNaam))
          mail_bericht += 'Bestand: %s is niet toegevoegd in Geonetwork. Let op!!!\n' %(xmlNaam)
  # loop door alle uuids uit de GN request
  for GNuuid in GNuuidDates.keys():
    # als de request uuid niet voorkomt in de uuids, verwijder hem dan uit GN
    if GNuuid not in fileUuids:
      # verwijder de overbodige xmls
      cswDelete = '<?xml version="1.0" encoding="UTF-8"?>\n'
      cswDelete += '<csw:Transaction xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" '
      cswDelete += 'xmlns:ogc="http://www.opengis.net/ogc" '
      cswDelete += 'xmlns:dc="http://www.purl.org/dc/elements/1.1/" '
      cswDelete += 'version="2.0.2" service="CSW">\n'
      cswDelete += '<csw:Delete typeName="csw:Record">\n'
      cswDelete += '<csw:Constraint version="1.0.0">\n'
      cswDelete += '<ogc:Filter>\n'
      cswDelete += '<ogc:PropertyIsEqualTo>\n'
      cswDelete += '<ogc:PropertyName>dc:Identifier</ogc:PropertyName>\n'
      cswDelete += '<ogc:Literal>%s</ogc:Literal>\n' %(GNuuid)
      cswDelete += '</ogc:PropertyIsEqualTo>\n'
      cswDelete += '</ogc:Filter>\n'
      cswDelete += '</csw:Constraint>\n'
      cswDelete += '</csw:Delete>\n'
      cswDelete += '</csw:Transaction>' 
      # verwijder het record
      try:
        response_delete = client.post(URL+"/geonetwork/srv/eng/csw-publication", data=cswDelete.encode('utf-8'), \
                          headers={'Content-Type': 'application/xml'}, auth=(user, password), verify=verifyRequest)
      # overige foutmeldingen
      except requests.exceptions.RequestException as foutje: 
        logging.error('Bij het verwijderen uit GN geeft bestand met UUID: %s foutmelding: %s' %(GNuuid, foutje))
        mail_bericht += 'Bij het verwijderen uit GN geeft bestand met UUID: %s foutmelding: %s\n' %(GNuuid, foutje)
        # ga naar de volgende xmlNaam
        continue
      # werk anders de logging, de mail en de teller bij
      else:
        if responseCount(response_delete, 'totalDeleted', '><') == 1:
          logging.info('Bestand met UUID: %s is verwijderd uit Geonetwork' %(GNuuid))
          mail_bericht += 'Bestand met UUID: %s is verwijderd uit Geonetwork\n' %(GNuuid)
          tellers[2] += 1
          tellers[3] -= 1
        else:
          logging.info('Bestand met UUID: %s is niet verwijderd uit Geonetwork. Let op!!!' %(GNuuid))
          mail_bericht += 'Bestand met UUID: %s is niet verwijderd uit Geonetwork. Let op!!!\n' %(GNuuid)
  # als er iets veranderd is stuur dan een mail naar de beheerders
  if mail_bericht:
    # lees de gegevens uit
    mail_gegevens = cfg.get('mail_gegevens')
    # vul de gegevens aan
    mail_gegevens['onderwerp'] = 'Bestand: %s is uitgevoerd' %(os.path.splitext(bestand)[0])
    bericht = 'Beste beheerder, \n\n\n'
    bericht += 'Bij de verwerking van %s zijn de volgende wijzigingen aangebracht:\n\n' %(os.path.splitext(bestand)[0])
    bericht += '%s\n\n' %(mail_bericht)
    bericht += 'aantal vervangen records: %s\n' %(tellers[0])
    bericht += 'aantal toegevoegde records: %s\n' %(tellers[1])
    bericht += 'aantal verwijderde records: %s\n' %(tellers[2])
    bericht += 'aantal aanwezige records: %s\n\n\n' %(tellers[3])
    bericht += '%s\n' %(mail_gegevens['bericht_naam'])
    bericht += '%s\n' %(mail_gegevens['bericht_org'])
    bericht += '%s\n' %(mail_gegevens['bericht_email'])
    bericht += '%s\n' %(mail_gegevens['bericht_post'])
    bericht += '%s  %s\n\n' %(mail_gegevens['bericht_postcode'], mail_gegevens['bericht_plaats'])
    bericht += '%s' %(mail_gegevens['bericht_www'])
    mail_gegevens['bericht'] = bericht
    # verstuur de mail
    Zendmail(mail_gegevens, SSL=False)
  # zet de aantallen in de logging
  logging.info('')
  logging.info('aantal vervangen records: %s' %(tellers[0]))
  logging.info('aantal toegevoegde records: %s' %(tellers[1]))
  logging.info('aantal verwijderde records: %s' %(tellers[2]))
  logging.info('aantal aanwezige records: %s' %(tellers[3]))
  logging.info('')
  # beperk de omvang van de log file
  beperk_log_file(log_file)

# ----- EINDE PROGRAMMA ------------------------------------------------
