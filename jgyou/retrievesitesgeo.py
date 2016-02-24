'''
retrievesitesgeo.py

This script takes street addresses from the drop-off sites data
to find geographic data from Opencage Data. 
(This site uses geocoding to convert addresses to longitude and latitude).
'''

from urllib import parse, request
from json import loads, dumps

import pymongo
import prov.model
import datetime
import uuid

exec(open('../pymongo_dm.py').read())

client = pymongo.MongoClient()
repo = client.repo

# remember to modify this line later
repo.authenticate("jgyou", "jgyou")

startTime = datetime.datetime.now()

##########

# authorization key
key = "8424241accce046b47502e65e4fc8a68"

repo.dropPermanent("sitegeocodes")
repo.createPermanent("sitegeocodes")

param = []

for site in repo['jgyou.currentsites'].find():	
	s = site['location_street_name'] + "," + site['neighborhood'] + ", MA" + " " + site['location_zipcode']
	param.append(s)

	query = "https://api.opencagedata.com/geocode/v1/geojson?q=" + parse.quote_plus(s) + "&limit=1" +\
	 "&pretty=1" + "&countrycode=us" +"&key=" + key
	georesult =  request.urlopen(query).read().decode("utf-8")
	geojs = json.loads(georesult)

	# tie together site id with coordinate data by adding a field to json
	geojs['siteid'] = str(site['_id'])
	georesult = dumps(geojs)

	# then insert database
	repo['jgyou.sitegeocodes'].insert(loads(georesult))


###########

endTime = datetime.datetime.now()

repo.logout()

# record provenance data

## go review different provs

provdoc = prov.model.ProvDocument()
provdoc.add_namespace('alg', 'http://datamechanics.io/algorithm/jgyou/') # The scripts in <folder>/<filename> format.
provdoc.add_namespace('dat', 'http://datamechanics.io/data/jgyou/') # The data sets in <user>/<collection> format.
provdoc.add_namespace('ont', 'http://datamechanics.io/ontology#') # 'Extension', 'DataResource', 'DataSet', 'Retrieval', 'Query', or 'Computation'.
provdoc.add_namespace('log', 'http://datamechanics.io/log#') # The event log.
provdoc.add_namespace('ocd', 'https://api.opencagedata.com/geocode/v1/')

# activity = invocation of script, agent = script, entity = resource
# agent
this_script = provdoc.agent('alg:retrievesitesgeo', {prov.model.PROV_TYPE:prov.model.PROV['SoftwareAgent'], 'ont:Extension':'py'})

# input data
dropoffsites = provdoc.entity('dat:currentsites', {prov.model.PROV_LABEL:'Current Drop-Off Sites', prov.model.PROV_TYPE:'ont:DataSet'})
resource = provdoc.entity('ocd:geocode', {'prov:label':'OpenCage Data', prov.model.PROV_TYPE:'ont:DataResource', 'ont:Extension':'geojson'})

# output dataset
sitecodesoutput = provdoc.entity('dat:sitegeocodes', {prov.model.PROV_LABEL:'Site Geocodes', prov.model.PROV_TYPE:'ont:DataSet'})

provdoc.wasAttributedTo(sitecodesoutput, this_script)

# record provenance for each geocode query
for i in param:
	this_run = provdoc.activity('log:a'+str(uuid.uuid4()), startTime, endTime, \
		{prov.model.PROV_TYPE:'ont:Retrieval', 'ont:Query':'?q=' + i + "&limit=1&countrycode=us"})
	
	provdoc.wasAssociatedWith(this_run, this_script)
	
	provdoc.used(this_run, resource, startTime)
	provdoc.used(this_run, dropoffsites, startTime)
	
	provdoc.wasGeneratedBy(sitecodesoutput, this_run, endTime)

	provdoc.wasDerivedFrom(sitecodesoutput, resource, this_run, this_run, this_run)
	provdoc.wasDerivedFrom(sitecodesoutput, dropoffsites, this_run, this_run, this_run)

repo.record(provdoc.serialize()) # Record the provenance document.








