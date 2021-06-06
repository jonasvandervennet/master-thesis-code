#!/bin/bash

echo "  Creating the function file ..."
echo ""
echo 'function main(params) {var name = params.name || "World"; return { payload:  "Hello, " + name + "!" }; }' > hello.js

echo "  Adding the function to whisk ..."
echo ""
wsk -i action create hello hello.js

echo "  Invoking the function ..."
echo ""
wsk -i action invoke hello --blocking --result --param name Yolotanker

echo "  Removing the function from whisk ..."
echo ""
wsk -i action delete hello

echo "  Deleting the function file ..."
echo ""
rm hello.js
