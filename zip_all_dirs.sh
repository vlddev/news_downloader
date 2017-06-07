for f in dt*
do
  if [ -d "$f" ]
  then
    echo "processing directory $f"
    zip -rj "$f.zip" $f
  fi
done
