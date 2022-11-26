"""
ADM Reader
"""

from struct import unpack, unpack_from, calcsize
from io import BytesIO
from collections import namedtuple
from typing import Iterable, Tuple

from lxml import etree as ET

ChannelEntry = namedtuple('ChannelEntry', "track_index uid track_ref pack_ref")

class WavADMReader:
    """
    Reads XML data from an EBU ADM (Audio Definiton Model) WAV File.
    """

    def __init__(self, axml_data: bytes, chna_data: bytes):
        header_fmt = "<HH"
        uid_fmt = "<H12s14s11sx"

        #: An :mod:`lxml.etree` of the ADM XML document
        self.axml = ET.parse(BytesIO(axml_data))

        _, uid_count = unpack(header_fmt, chna_data[0:4])

        #: A list of :class:`ChannelEntry` objects parsed from the
        #: `chna` metadata chunk. 
        self.channel_uids = []

        offset = calcsize(header_fmt)
        for _ in range(uid_count):

            track_index, uid, track_ref, pack_ref = unpack_from(uid_fmt, chna_data, offset)

            # these values are either ascii or all null

            self.channel_uids.append(ChannelEntry(track_index,
                uid.decode('ascii') , track_ref.decode('ascii'), pack_ref.decode('ascii')))

            offset += calcsize(uid_fmt)


    def track_info(self, index):
        """
        Information about a track in the WAV file.

        :param index: index of audio track (indexed from zero) 
        :returns: a dictionary with *content_name*, *content_id*, *object_name*, *object_id*, 
            *pack_format_name*, *pack_type*, *channel_format_name*
        """
        channel_info = next((x for x in self.channel_uids if x.track_index == index + 1), None)
        
        if channel_info is None:
            return None

        ret_dict = {}

        nsmap = self.axml.getroot().nsmap

        afext = self.axml.find(".//audioFormatExtended", namespaces=nsmap)

        trackformat_elem = afext.find(".//audioTrackFormat[@audioTrackFormatID='%s']" % channel_info.track_ref, 
            namespaces=nsmap)

        stream_id = trackformat_elem[0].text

        channelformatref_elem = afext.find(".//audioStreamFormat[@audioStreamFormatID='%s']/audioChannelFormatIDRef" % stream_id, 
            namespaces=nsmap)
        channelformat_id = channelformatref_elem.text

        packformatref_elem = afext.find(".//audioStreamFormat[@audioStreamFormatID='%s']/audioPackFormatIDRef" % stream_id, 
            namespaces=nsmap)
        packformat_id = packformatref_elem.text

        channelformat_elem = afext.find(".//audioChannelFormat[@audioChannelFormatID='%s']" % channelformat_id, 
            namespaces=nsmap)
        ret_dict['channel_format_name'] = channelformat_elem.get("audioChannelFormatName")

        packformat_elem = afext.find(".//audioPackFormat[@audioPackFormatID='%s']" % packformat_id, 
            namespaces=nsmap)
        ret_dict['pack_type'] = packformat_elem.get("typeDefinition")
        ret_dict['pack_format_name'] = packformat_elem.get("audioPackFormatName")

        object_elem = afext.find(".//audioObject[audioPackFormatIDRef = '%s']" % packformat_id, 
            namespaces=nsmap)

        ret_dict['audio_object_name'] = object_elem.get("audioObjectName")
        object_id = object_elem.get("audioObjectID")
        ret_dict['object_id'] = object_id

        content_elem = afext.find(".//audioContent/[audioObjectIDRef = '%s']" % object_id, 
            namespaces=nsmap)

        ret_dict['content_name'] = content_elem.get("audioContentName")
        ret_dict['content_id'] = content_elem.get("audioContentID")

        return ret_dict

    def to_dict(self):
        """
        Get ADM metadata as a dictionary.
        """

        def make_entry(channel_uid_rec):
            rd = channel_uid_rec._asdict()
            rd.update(self.track_info(channel_uid_rec.track_index - 1))
            return rd

        return dict(channel_entries=list(map(lambda z: make_entry(z), self.channel_uids)))