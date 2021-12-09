## Installation

### Requirements

#### Linux

#### Python

### Choosing a database engine

This table will help you chose a database backend that suits your needs.

|-|sqlite|postgresql|timescaledb|
|-|--|-|-|
|supported version|||
|when to use|local development|Docker environment, prodection instances|same as pg but timeseries
|performance|average|good|great in some scenarios|
|caveats and limitations|sql hooks immune tables|1,2|incomp,missing methods|

1 see reindexing
2 see hasura limitations

### poetry (recommended)

install and configure poetry
add dependency
almost semantic, break queckly

### pip requirements.txt
