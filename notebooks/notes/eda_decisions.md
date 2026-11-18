# EDA decisions

Consolidated notes from the three section notebooks. The `src/` pipeline implements these rules; the notebooks are kept as documentation.


## Devices (section 1)

# The following section details the EDA conclusions for the first CSV (devices).

## Context

The CSV in use is "devices(...)"

The column manufacturer_id looks like it will be a foreign key to another CSV in the study case.

I can drop rows with null values. (Having in mind that this is an exploratory analysis for a forward report in Power BI)  
| Column | Null percentage (%) |
| :--- | :--- |
| quantity_in_commerce |    72.99850 |  
| risk_class |             72.136762 |  
| distributed_to |         71.563396 |  
| implanted |              70.487700 |  
| classification |         69.893191 |  
| code |                   69.371411 |  
| number |                 46.046055 |

For this analysis I will drop the "updated_at" column.

Initially the only numeric columns I have in this CSV are id and manufacturer_id.

The manufacturer_id column will be used for analysis with the other CSVs.
It appears to be a foreign key.

Rows will be dropped by columns.
This will leave us with 30556 rows and 14 columns.
A much smaller amount of data than the initial amount, but the initial amount had too much noise in NaN values.

Analysis of the current dataframe size indicates that of 33024 devices only 7174 have been implanted.

Of these, none have been classified as Class I (A situation where there is a reasonable chance that a product will cause serious health problems or death.)

Change the risk_class column values from 'Not Classified' to 'Unclassified' to unify them because they are the same:
test.loc[test['risk_class'] == 'Not Classified', 'risk_class'] = 'Unclassified'

distributed_to column will help in forward analysis.

I think 'number' column won't be useful in the forward analysis.

I won't use the information in the 'number' column. I can drop it.

The column slug may be related to another CSV, analyze that and if it's not, drop it.

Drop country column.


## Events (section 2)

Here I'm going to write the annotations and pre-conclusions of the EDA. (preliminary and formal EDA)

'url' column will be dropped (http 302 response)

| More than 95% null columns will be dropped. | Missing | % |
| --- | --- | --- |
| date_updated | 124738 | 99.82 |
| target_audience | 124529 | 99.65 |
| action_level | 122513 | 98.03 |
| create_date | 119768 | 95.84 |

The columns 'created_at' and 'updated_at' are the same, going to drop the second one.

For this exploratory analysis I won't use the column 'action_summary', so I will drop it.

'documents' links won't work, will be dropped and not used in this analysis.

'action_classification' will be dropped (Won't use the information in that column for the analysis)

'authorities_link' won't be used for the analysis.

'data_notes' won't be used due to 54% null values.

'date_posted' will be dropped.

'date_terminated' will be dropped.

'status' will be dropped.

I won't use 'create_date' column, not enough data.

I won't use 'date' column, not enough data.

At this moment we can make an inner join on 'device_id' and csv_devices id.


## Manufacturers (section 3)

`representative` (97.68% null), `comment` (91.17%) and `address` (81.25%) were dropped. `updated_at` was dropped because it duplicates `created_at`. The 37 rows without `name` were removed. `name` is not unique (20,049 distinct names over 31,790 ids), so the dashboard joins and counts by `id`.
