<!DOCTYPE html>
<html>
  <head>
    <title>Mechanical Turk Contract Verification</title>
  </head>
  <body>
    <h1>Mechanical Turk Contract Verification</h1>
    <textarea name="contract"><?php echo $CONTRACT; ?></textarea>
    <form name="contractverification" id="contractverification" action="form.php" method="post">
    <input type="radio" name="contractstatus" value="complete"> Contract Is Complete <br>
    <input type="radio" name="contractstatus" value="incompletetoseller"> Seller Failed To Complete <br>
    <input type="radio" name="contractstatus" value="incompletetobuyer"> Buyer Failed To Complete <br>
    <input type="submit" value="Submit"> <br>
    </form>
  </body>
</html>
