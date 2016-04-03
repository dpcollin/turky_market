<?php
$result = $_POST['contractstatus'];
$resultfile = fopen("resultfile.txt", "w") or die("File missing/Unable to open");
fwrite($resultfile, $result);
$D = date_create();
$DD = date_timestamp_get($date);
fwrite($resultfile, $DD);
fclose($resultfile);
echo "Completion Code :$DD);
?>
