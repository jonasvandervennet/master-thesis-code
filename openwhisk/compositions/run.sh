#!/bin/bash

wsk action invoke $1 -i -P $1-parameters.json  --blocking --result 