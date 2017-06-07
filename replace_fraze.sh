cd $1
for f in */*.fb2
do
  echo "processing $f"
  sed -i "s/<p>Читайте також/<p>Читайте_також: /g;" $f
done
