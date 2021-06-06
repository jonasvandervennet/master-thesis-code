#!/bin/bash

compose $1.js > $1-composition.json
deploy $1 $1-composition.json -iw