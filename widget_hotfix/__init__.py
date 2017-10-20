"""
The arcgis.widgets module provides components for visualizing GIS data and analysis.
This module includes the MapView Jupyter notebook widget for visualizing maps and layers
"""
import json
import random
import string

from arcgis.features import FeatureSet
from arcgis.raster import ImageryLayer
from arcgis.gis import Layer
from arcgis.gis import Item
from arcgis.mapping import WebMap

try:
    from ipywidgets import widgets
except:
    from IPython.html import widgets

try:
    from traitlets import Unicode, Int, List, Bool, Dict
except:
    from IPython.utils.traitlets import Unicode, Int, List, Bool, Dict


class MapView(widgets.DOMWidget):
    """Mapping widget for Jupyter Notebook"""
    _view_name = Unicode('MapView').tag(sync=True)
    _view_module = Unicode('mapview').tag(sync=True)

    # value = Unicode('Hello World!').tag(sync=True)

    _basemap = Unicode('topo').tag(sync=True)
    basemaps = List([]).tag(sync=True)
    _gallerybasemaps = List([]).tag(sync=True)
    _gbasemaps_def = List([]).tag(sync=True)
    width = Unicode('100%').tag(sync=True)
    zoom = Int(2).tag(sync=True)
    id = Unicode('').tag(sync=True)
    center = List([0, 0]).tag(sync=True)
    mode = Unicode('navigate').tag(sync=True)
    _addlayer = Unicode('').tag(sync=True)
    start_time = Unicode('').tag(sync=True)
    end_time = Unicode('').tag(sync=True)
    _extent = Unicode('').tag(sync=True)
    _jsextent = Unicode('').tag(sync=True)
    _token_info = Unicode('').tag(sync=True)

    _arcgis_url = Unicode('').tag(sync=True)

    _swipe_div = Unicode('').tag(sync=True)

    _gallery_initialized = False # Used to keep track if GalleryBasemaps has been called

    def __init__(self, **kwargs):
        """Constructor of Map widget.
        Accepts the following keyword arguments:
        gis     The gis instance with which the map widget works, used for authentication, and adding secure layers and private items from that GIS
        item    webmap item from portal with which to initialize the map widget
        """
        super(MapView, self).__init__(**kwargs)
        self._click_handlers = widgets.CallbackDispatcher()
        self._draw_end_handlers = widgets.CallbackDispatcher()

        self.on_msg(self._handle_map_msg)

        self.basemaps = ['dark-gray',
                        'dark-gray-vector',
                        'gray',
                        'gray-vector',
                        'hybrid',
                        'national-geographic',
                        'oceans',
                        'osm',
                        'satellite',
                        'streets',
                        'streets-navigation-vector',
                        'streets-night-vector',
                        'streets-relief-vector',
                        'streets-vector',
                        'terrain',
                        'topo',
                        'topo-vector']
        self._swipe_div = 'swipeDiv' + ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(6))

        self._gis = kwargs.pop('gis', None)
        if self._gis is not None and self._gis._con._username is not None:  # not anonymous
            token_info = {
                "server": self._gis._con.baseurl.replace('http://', 'https://'),
                "tokenurl": (self._gis._con.baseurl +
                             'generateToken').replace('http://', 'https://'),
                "username": self._gis._con._username,
                "password": self._gis._con._password
            }
            self._token_info = json.dumps(token_info)
            # if self._gis.properties.portalName != 'ArcGIS Online':
            self._arcgis_url = self._gis._con.baseurl + 'content/items'

        self.item = kwargs.pop('item', None)
        if self.item is not None:
            if isinstance(self.item, WebMap):
                self.item = self.item.item
            if 'type' in self.item and self.item.type.lower() != 'web map':
                raise TypeError("item type must be web map")
            self.id = self.item.id

    def draw(self, shape, popup=None, symbol=None, attributes=None):
        """
        Draws a shape.

        Arguments:
        shape is one of ["circle", "downarrow", "ellipse", "extent", "freehandpolygon",
        "freehandpolyline", "leftarrow", "line", "multipoint", "point", "polygon", "polyline",
        "rectangle", "rightarrow", "triangle", "uparrow", or geometry dict object]

        popup is a dict containing "title" and "content" as keys that will be displayed
        when the shape is clicked

        symbol is a symbol specified in json format as described at http://resources.arcgis.com/en/help/arcgis-rest-api/index.html#//02r3000000n5000000
        a default symbol is used is one is not specified.
        Tip: a helper utility to get the symbol format for several predefined symbols is available at
        http://esri.github.io/arcgis-python-api/tools/symbol.html

        attributes is a dict containing name value pairs of fields and field values
        associated with the graphic.

        """
        if isinstance(shape, list) and len(shape) == 2:  # [lat, long] pair
            shape = {'x': shape[1], 'y': shape[0], "spatialReference": {"wkid": 4326}, 'type': 'point'}
        elif isinstance(shape, tuple):  # (lat, long) pair
            shape = {'x': shape[1], 'y': shape[0], "spatialReference": {"wkid": 4326}, 'type': 'point'}
        elif isinstance(shape, dict) and 'location' in shape: # geocoded location
            shape = {'x': shape['location']['x'], 'y': shape['location']['y'],
                     "spatialReference": {"wkid": 4326}, 'type': 'point'}

        if isinstance(shape, FeatureSet):
            fset = shape
            for feature in fset.features:
                graphic = {
                    "geometry": feature.geometry,
                    "infoTemplate": popup,
                    "symbol": symbol,
                    "attributes": feature.attributes
                }
                self.mode = json.dumps(graphic)
        elif isinstance(shape, dict):
            graphic = {
                "geometry": shape,
                "infoTemplate": popup,
                "symbol": symbol,
                "attributes": attributes
            }
            self.mode = json.dumps(graphic)
            # print(json.dumps(graphic))
        else:
            self.mode = shape

    def add_layer(self, item, options=None):
        """
        Adds layers from the provided item
        """
        if isinstance(item, list):
            for lyr in item:
                self.add_layer(lyr, options)

        elif isinstance(item, dict) and 'function_chain' in item:
            js_layer = item['layer']._lyr_json
            options_dict = {
                    "imageServiceParameters": {
                        "renderingRule": item['function_chain']
                    }
                }

            if options is not None:
                options_dict.update(options)

            js_layer.update({
                "options": json.dumps(options_dict)
            })
            self._addlayer = json.dumps(js_layer)
        elif isinstance(item, Layer):
            js_layer = item._lyr_json
            if options is not None:
                if 'options' in js_layer:  # ImageryLayers may have rendering rules in options
                    lyr_options = json.loads(js_layer['options'])
                    lyr_options.update(options)
                    js_layer.update({'options': json.dumps(lyr_options)})
                else:
                    js_layer.update({"options": json.dumps(options)})

            self._addlayer = json.dumps(js_layer)
        elif 'layers' in item:  # items as well as services
            if item.layers is None:
                raise RuntimeError('No layers accessible/available in this item or service')
            for lyr in item.layers:
                js_layer = lyr._lyr_json
                if options is not None:
                    js_layer.update({"options": json.dumps(options)})
                self._addlayer = json.dumps(js_layer)
        else:  # dict {'url':'xxx', 'type':'yyy', 'opacity':'zzz' ...}
            if options is not None:
                item.update({"options": json.dumps(options)})

            self._addlayer = json.dumps(item)

    def clear_graphics(self):
        self.mode = "###clear_graphics"

    def set_time_extent(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time

    def remove_layers(self):
        self.mode = "###remove_layers"


    @property
    def gallery_basemaps(self):
        """
        Retrieves the portal's custom basemap group and populates properties
        """
        if not self._gallery_initialized:
        #if len(self._gallerybasemaps) == 0:
            bmlyrs = []
            bms = []
            bmquery = self._gis.properties['basemapGalleryGroupQuery']
            basemapsgrp = self._gis.groups.search(bmquery, outside_org=True)
            if len(basemapsgrp) == 1:
                for bm in basemapsgrp[0].content():
                    if bm.type.lower() == 'web map': # Only use WebMaps
                        bms.append(bm.title.lower().replace(" ", "_"))  # item title will be name
                        item_data = bm.get_data()  # we have to get JSON definition to pass through
                        if item_data is not None:
                            bmlyrs.append(item_data['baseMap']['baseMapLayers'])
                #self._gbasemaps_def = bmlyrs
                self._gbasemaps_def = self._gbasemaps_def + bmlyrs
                #nm = self._gis.properties['defaultBasemap']['title']
                #print("Loading Gallery Basemaps....")
                #self._gallerybasemaps = bms
                self._gallerybasemaps = self._gallerybasemaps + bms
                self._gallery_initialized = True
                return self._gallerybasemaps
            else:
                #print("Basemap Group '" + str(bmquery) + "' could not be found...")
                #return [] # If unable to find the group, return empty list
                return self._gallerybasemaps # Return whatever state List is in, even if empty
        else:
            return self._gallerybasemaps

    @property
    def basemap(self):
        return self._basemap

    @basemap.setter
    def basemap(self, value):
        if isinstance(value, str):
            if (value in self.basemaps):
                self._basemap = value
            elif (value in self.gallery_basemaps): # this should initialize
                self._basemap = value
            else:
                print("Basemap '" + str(value) + "' is not a valid basemap name.")

        # Allow for a WebMap item to be passed in and set.  This is useful if someone
        #  finds some other WebMap in AGOL/Portal that they would like to use in this
        #  notebook.  In this case, you need to add it to the current set.
        #  This will utilize the gallery_basemaps objects for adding the new basemap.
        #elif (isinstance(value, Item)):
        #    if value.type.lower() == "web map":
        #        webmapitem = value
        #        bmlyrs = []
        #        bms = []
        #        bms.append(webmapitem.title.lower().replace(" ", "_")) # item title will be name
        #        item_data = webmapitem.get_data()  # we have to get JSON definition to pass through
        #        if item_data is not None:
        #            bmlyrs.append(item_data['baseMap']['baseMapLayers'])
        #            self._gbasemaps_def = self._gbasemaps_def + bmlyrs
        #            self._gallerybasemaps = self._gallerybasemaps + bms
        #            self._basemap = bms[0]
        #            print('Set Map Widget Basemap to WebMap Item basemap layers.')
        #        else:
        #            print("WebMap item appears to have no item_data.")

    @property
    def extent(self):
        if self._jsextent is not None and self._jsextent != '':
            return json.loads(self._jsextent)
        else:
            return None

    @extent.setter
    def extent(self, value):
        if isinstance(value, (tuple, list)):
            if all(isinstance(el, list) for el in value):
                extent = {
                    'xmin': value[0][0],
                    'ymin': value[0][1],
                    'xmax': value[1][0],
                    'ymax': value[1][1]
                }
                value = extent
        self._extent = json.dumps(value)

    def on_click(self, callback, remove=False):
        """Register a callback to execute when the map is clicked.

        The callback will be called with one argument,
        the clicked widget instance.

        Parameters
        ----------
        remove : bool (optional)
            Set to true to remove the callback from the list of callbacks."""
        self._click_handlers.register_callback(callback, remove=remove)

    def on_draw_end(self, callback, remove=False):
        """Register a callback to execute when something is drawn

        The callback will be called with two argument,
        the clicked widget instance, and the geometry drawn

        Parameters
        ----------
        remove : bool (optional)
            Set to true to remove the callback from the list of callbacks."""
        self._draw_end_handlers.register_callback(callback, remove=remove)

    # def _handle_map_msg(self, _, content):
    def _handle_map_msg(self, _, content, buffers):
        """Handle a msg from the front-end.

        Parameters
        ----------
        content: dict
            Content of the msg."""

        if content.get('event', '') == 'mouseclick':
            self._click_handlers(self, content.get('message', None))
        if content.get('event', '') == 'draw-end':
            self._draw_end_handlers(self, content.get('message', None))