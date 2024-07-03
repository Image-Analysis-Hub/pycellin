#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class Model:

    """What do I need here on top of data and metadata?
    - an ID (string or number), can be the name of the file when it is built from a TM file
    - a provenance field? (mandatory) TM, CTC...
    - a date? (mandatory) can be useful for traceability
    - the version of Pycellin that was used to build the model? (mandatory) can be useful for traceability
    - a description in which people can put whatever they want (string, facultative),
      or maybe a dict with a few keys (description, author, etc.) that can be defined 
      by the users
    - and I'm probably forgetting something...
    
    """
    

    def __init__(self):
        self.metadata = None
        self.coredatas = None

    def __init__(self, trackmate_file: str):
        pass

    def add_feature(self):
        # Need to update the metadata and the data
        pass

    def export(self, path: str, format: str):
        """Export to another format, e.g. TrackMate."""
        pass


