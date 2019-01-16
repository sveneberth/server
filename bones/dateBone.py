# -*- coding: utf-8 -*-
from server.bones import baseBone
from server import request
# FIXME: that first time import was shadowed by the next time import - do we need the now spelled time_time anymore?
from time import time as time_time, mktime
from datetime import time, datetime, timedelta
import logging
try:
	import pytz
except:
	pytz = None


## Workaround for Python Bug #7980 - time.strptime not thread safe
datetime.now().strptime("2010%02d%02d"%(1,1),"%Y%m%d")
datetime.now().strftime("%Y%m%d")


class ExtendedDateTime( datetime ):
	def totimestamp( self ):
		"""Converts this DateTime-Object back into Unixtime"""
		return( int( round( mktime( self.timetuple() ) ) ) )

	def strftime(self, format ):
		"""
		Provides correct localized names for directives like %a which don't get translated on GAE properly
		This currently replaces %a, %A, %b, %B, %c, %x and %X.

		:param format: String containing the Format to apply.
		:type format: str
		:returns: str
		"""
		if "%c" in format:
			format = format.replace("%c", _("const_datetimeformat") )
		if "%x" in format:
			format = format.replace("%x", _("const_dateformat") )
		if "%X" in format:
			format = format.replace("%X", _("const_timeformat") )
		if "%a" in format:
			format = format.replace( "%a", _("const_day_%s_short" % int( super( ExtendedDateTime, self ).strftime("%w") ) ) )
		if "%A" in format:
			format = format.replace( "%A", _("const_day_%s_long" % int( super( ExtendedDateTime, self ).strftime("%w") ) ) )
		if "%b" in format:
			format = format.replace( "%b", _("const_month_%s_short" % int( super( ExtendedDateTime, self ).strftime("%m") ) ) )
		if "%B" in format:
			format = format.replace( "%B", _("const_month_%s_long" % int( super( ExtendedDateTime, self ).strftime("%m") ) ) )
		return( super( ExtendedDateTime, self ).strftime( format.encode("UTF-8") ).decode("UTF-8") )


class dateBone( baseBone ):
	type = "date"

	@staticmethod
	def generageSearchWidget(target,name="DATE BONE",mode="range"):
		return ( {"name":name,"mode":mode,"target":target,"type":"date"} )


	def __init__( self,  creationMagic=False, updateMagic=False, date=True, time=True, localize=False, *args,  **kwargs ):
		"""
			Initializes a new dateBone.

			:param creationMagic: Use the current time as value when creating an entity; ignoring this bone if the
				entity gets updated.
			:type creationMagic: bool
			:param updateMagic: Use the current time whenever this entity is saved.
			:type updateMagic: bool
			:param date: Should this bone contain a date-information?
			:type date: bool
			:param time: Should this bone contain time information?
			:type time: bool
			:param localize: Automatically convert this time into the users timezone? Only valid if this bone
				contains date and time-information!
			:type localize: bool
		"""
		baseBone.__init__( self,  *args,  **kwargs )
		if creationMagic or updateMagic:
			self.readonly = True
			self.visible = False
		self.creationMagic = creationMagic
		self.updateMagic = updateMagic
		if not( date or time ):
			raise ValueError("Attempt to create an empty datebone! Set date or time to True!")
		if localize and not ( date and time ):
			raise ValueError("Localization is only possible with date and time!")
		self.date=date
		self.time=time
		self.localize = localize

	def fromClient( self,valuesCache, name, data ):
		"""
			Reads a value from the client.
			If this value is valid for this bone,
			store this value and return None.
			Otherwise our previous value is
			left unchanged and an error-message
			is returned.

			:param name: Our name in the skeleton
			:type name: str
			:param data: *User-supplied* request-data
			:type data: dict
			:returns: str or None
		"""

		# FIXME: too much or unneeded unicode conversions of rawValue!!!
		rawValue = data.get(name, None)
		if not rawValue:
			value = None
		elif unicode(rawValue).replace("-",  "",  1).replace(".","",1).isdigit():
			if int(rawValue) < -1*(2**30) or int(rawValue)>(2**31)-2:
				value = False  # its invalid
			else:
				value = ExtendedDateTime.fromtimestamp( float(rawValue) )
		elif not self.date and self.time:
			try:
				# that should be more efficient, backward compatible and also includes microseconds when provided
				rawValue = unicode(rawValue)
				colonCount = rawValue.count(u":")
				if colonCount > 1:
					timeComponents = [int(x.strip()) for x in rawValue.split(u":")]
					value = time(*timeComponents)
				elif colonCount > 0:
					hour, minute = [int(x.strip()) for x in rawValue.split(u":")]
					value = time(hour=hour, minute=minute)
				elif rawValue.replace(u"-",  u"",  1).isdigit():
					value = time(second=int(rawValue))
				else:
					value = False  # its invalid
			except Exception as err:
				logging.error("dateBone.fromClient - exception occured!")
				logging.exception(err)
				value = False
		elif unicode(rawValue).lower().startswith("now"):
			tmpRes = ExtendedDateTime.now()
			if len(unicode(rawValue))>4:
				try:
					tmpRes += timedelta(seconds= int(unicode(rawValue)[3:]))
				except:
					pass
			value = tmpRes
		else:
			try:
				rawValue = unicode(rawValue)
				if u" " in rawValue:  # Date with time
					try:  # Times with seconds
						colonCount = rawValue.count(u":")
						if colonCount == 3:  # including microseconds
							if "-" in rawValue:  # ISO Date
								value = ExtendedDateTime.strptime(rawValue, "%Y-%m-%d %H:%M:%S:%f")
							elif "/" in rawValue:  # Ami Date
								value = ExtendedDateTime.strptime(rawValue, "%m/%d/%Y %H:%M:%S:%f")
							else:  # European Date
								value = ExtendedDateTime.strptime(rawValue, "%d.%m.%Y %H:%M:%S:%f")
						else:  # just seconds
							if "-" in rawValue:  # ISO Date
								value = ExtendedDateTime.strptime(rawValue, "%Y-%m-%d %H:%M:%S")
							elif "/" in rawValue:  # Ami Date
								value = ExtendedDateTime.strptime(rawValue, "%m/%d/%Y %H:%M:%S")
							else:  # European Date
								value = ExtendedDateTime.strptime(rawValue, "%d.%m.%Y %H:%M:%S")
					except:
						if "-" in rawValue:  # ISO Date
							value = ExtendedDateTime.strptime(rawValue, "%Y-%m-%d %H:%M")
						elif "/" in rawValue:  # Ami Date
							value = ExtendedDateTime.strptime(rawValue, "%m/%d/%Y %H:%M")
						else:  # European Date
							value = ExtendedDateTime.strptime(rawValue, "%d.%m.%Y %H:%M")
				else:
					if "-" in rawValue:  # ISO (Date only)
						value = ExtendedDateTime.strptime(rawValue, "%Y-%m-%d")
					elif "/" in rawValue:  # Ami (Date only)
						value = ExtendedDateTime.strptime(rawValue, "%m/%d/%Y")
					else:  # European (Date only)
						value =ExtendedDateTime.strptime(rawValue, "%d.%m.%Y")
			except:
				value = False  # its invalid

		if value is False:
			return "Invalid value entered"
		else:
			err = self.isInvalid(value)
			if not err:
				valuesCache[name] = value
				if value is None:
					return "No value entered"
			return err

	def isInvalid(self, value):
		"""
			Ensure that year is >= 1900
			Otherwise strftime will break later on.
		"""
		if isinstance(value, datetime):
			if value.year < 1900:
				return "Year must be >= 1900"
		return super(dateBone, self).isInvalid(value)

	def guessTimeZone(self):
		"""
		Guess the timezone the user is supposed to be in.
		If it cant be guessed, a safe default (UTC) is used
		"""
		timeZone = "UTC" # Default fallback
		try:
			# Check the local cache first
			if "timeZone" in request.current.requestData():
				return( request.current.requestData()["timeZone"] )
			headers = request.current.get().request.headers
			if "X-Appengine-Country" in headers:
				country = headers["X-Appengine-Country"]
			else:  # Maybe local development Server - no way to guess it here
				return( timeZone )
			tzList = pytz.country_timezones[ country ]
		except:  # Non-User generated request (deferred call; task queue etc), or no pytz
			return( timeZone )
		if len( tzList ) == 1:  # Fine - the country has exactly one timezone
			timeZone = tzList[ 0 ]
		elif country.lower()=="us":  # Fallback for the US
			timeZone = "EST"
		elif country.lower() == "de":  # For some freaking reason Germany is listed with two timezones
			timeZone = "Europe/Berlin"
		else:  # The user is in a Country which has more than one timezone
			# Fixme: Is there any equivalent of EST for australia?
			pass
		request.current.requestData()["timeZone"] = timeZone #Cache the result
		return( timeZone )

	def readLocalized(self, value ):
		"""Read a (probably localized Value) from the Client and convert it back to UTC"""
		res = value
		if not self.localize or not value or not isinstance( value, datetime) :
			return( res )
		#Nomalize the Date to UTC
		timeZone = self.guessTimeZone()
		if timeZone!="UTC" and pytz:
			utc = pytz.utc
			tz = pytz.timezone( timeZone )
			#FIXME: This is ugly as hell.
			# Parsing a Date which is inside DST of the given tz dosnt change the tz-info,
			# and normalizing the whole thing changes the other values, too
			# So we parse the whole thing, normalize it (=>get the correct DST-Settings), then replacing the parameters again
			# and pray that the DST-Settings are still valid..
			res = ExtendedDateTime(value.year, value.month, value.day, value.hour, value.minute, value.second, value.microsecond, tzinfo=tz)
			res = tz.normalize(res)  # Figure out if its in DST or not
			res = res.replace(year=value.year, month=value.month, day=value.day, hour=value.hour, minute=value.minute, second=value.second, microsecond=value.microsecond)  # Reset the original values
			res = utc.normalize(res.astimezone(utc))
		return res

	def serialize(self, valuesCache, name, entity):
		res = valuesCache.get(name)
		if res:
			res = self.readLocalized( datetime.now().strptime(res.strftime("%d.%m.%Y %H:%M:%S:%f"), "%d.%m.%Y %H:%M:%S:%f"))

			# Crop unwanted values to zero
			if not self.time:
				res = res.replace(hour=0, minute=0, second=0, microsecond=0)
			elif not self.date:
				res = res.replace(year=1970, month=1, day=1)

		entity.set( name, res, self.indexed )
		return entity

	def unserialize(self, valuesCache, name, expando):
		if name not in expando:
			valuesCache[name] = None
			return
		valuesCache[name] = expando[ name ]
		if valuesCache[name] and (isinstance(valuesCache[name], float) or isinstance(valuesCache[name], int)):
			if self.date:
				self.setLocalized(valuesCache, name, ExtendedDateTime.fromtimestamp(valuesCache[name]))
			else:
				# TODO: do we have or can we retain microseconds here?
				valuesCache[name] = time(hour=int(valuesCache[name] / 60), minute=int(valuesCache[name] % 60))
		elif isinstance( valuesCache[name], datetime ):
			try:
				self.setLocalized(valuesCache, name, ExtendedDateTime.now().strptime(valuesCache[name].strftime("%d.%m.%Y %H:%M:%S:%f"), "%d.%m.%Y %H:%M:%S:%f"))
			except Exception as err:
				logging.exception(err)
				self.setLocalized(valuesCache, name, ExtendedDateTime.now().strptime(valuesCache[name].strftime("%d.%m.%Y %H:%M:%S"), "%d.%m.%Y %H:%M:%S"))
		else:
			# We got garbarge from the datastore
			valuesCache[name] = None
		return

	def setLocalized(self, valuesCache, name, value):
		""" Converts a Date read from DB (UTC) to the requesters local time"""
		valuesCache[name] = value
		if not self.localize or not value or not isinstance( value, ExtendedDateTime) :
			return
		timeZone = self.guessTimeZone()
		if timeZone!="UTC" and pytz:
			utc = pytz.utc
			tz = pytz.timezone(timeZone)
			value = tz.normalize(value.replace(tzinfo=utc).astimezone(tz))
			value = ExtendedDateTime(
				value.year,
				value.month,
				value.day,
				value.hour,
				value.minute,
				value.second,
				value.microsecond)
		valuesCache[name] = value

	def buildDBFilter( self, name, skel, dbFilter, rawFilter, prefix=None ):
		for key in [ x for x in rawFilter.keys() if x.startswith(name) ]:
			resDict = {}
			if not self.fromClient( resDict, key, rawFilter ): #Parsing succeeded
				super( dateBone, self ).buildDBFilter( name, skel, dbFilter, {key:datetime.now().strptime(resDict[key].strftime( "%d.%m.%Y %H:%M:%S" ), "%d.%m.%Y %H:%M:%S"  )}, prefix=prefix )
		return( dbFilter )

	def performMagic( self, valuesCache, name, isAdd ):
		if (self.creationMagic and isAdd) or self.updateMagic:
			self.setLocalized( valuesCache, name, ExtendedDateTime.now() )
