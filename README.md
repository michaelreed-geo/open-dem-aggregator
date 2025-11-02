# Open DEM Aggregator

**Op**en **Dem Agg**regator is a Python package that aggregates open data Digital Elevation Models
(DEM) and makes them accessible via a unified API. The package came about from frustration in
having to interact with the several different platforms for open DEM data held by governments and
agencies across the different nations of the United Kingdom.

The package also includes functionality to automate the clipping of DEM tiles and creation of
mosaics to specified areas of interest. This simplifies the download and processing of DEMs for use
in GIS.

## Supported open datasets

| Country/Region | Type            | Host                                                                     | Platform                       | Url                                                 |
|----------------|-----------------|--------------------------------------------------------------------------|--------------------------------|-----------------------------------------------------|
| England        | Onshore DTM/DSM | UK Government - Department for Environment, Food & Rural Affairs (Defra) | Defra Survey Data              | https://environment.data.gov.uk/survey              |
| Scotland       | Onshore DTM/DSM | Scottish Government                                                      | Scottish Remote Sensing Portal | https://remotesensingdata.gov.scot/                 |
| Wales          | Onshore DTM/DSM | Welsh Government, Natural Resources Wales                                | DataMapWales                   | https://datamap.gov.wales/maps/lidar-data-download/ |


## Future plans
* Add support for LAS/LAZ point clouds
* Develop QGIS plugin that uses this package to download and import data to GIS
* Add support for datasets in Ireland
* Add support for bathymetric (offshore) data covering UK, Ireland and Europe