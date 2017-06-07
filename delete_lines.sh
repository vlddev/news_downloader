#delete lines from files
#cd $1
for f in /home/vlad/Dokumente/python/site_downloader/dzerkalo_tyzhnja/dt_news_2015/*.fb2
do
  echo "processing $f"
  sed -i '/<p><<\/p>/d; /<p>><\/p>/d; /(document)\.ready(function()/d;
              /scrollpane\.gallery/d;
              /\.gallery_article/d;
              /\.gallery_main/d; /<p>})<\/p>/d;' $f
done
