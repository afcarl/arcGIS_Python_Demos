#Copy the text below to a new cell and run it
%%capture
!cp ./widget_hotfix/* ../conda/share/jupyter/nbextensions/arcgis
!cp ./widget_hotfix/* ../conda/lib/python3.6/site-packages/arcgis/widgets
!pip install jupyter_dashboards
!jupyter nbextension install --py jupyter_dashboards --user
!jupyter nbextension enable jupyter_dashboards --user --py
!jupyter nbextension enable --py --sys-prefix widgetsnbextension

# refresh browser after running cell. 