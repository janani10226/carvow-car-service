<!DOCTYPE html>
<html>
<head>
    <title>Appointment History</title>
    <style>
        body{
            font-family: Arial;
            background-color: #f5f5f5;
            padding: 20px;
        }
        h1{
            text-align: center;
        }
        table{
            width: 100%;
            border-collapse: collapse;
            background: white;
        }
        th, td{
            padding: 12px;
            border: 1px solid gray;
            text-align: center;
        }
        th{
            background-color: black;
            color: white;
        }
    </style>
    <!-- Auto-refresh every 5 seconds -->
    <meta http-equiv="refresh" content="5">
</head>
<body>

<h1>Appointment History</h1>

<table>
    <tr>
        <th>ID</th>
        <th>Name</th>
        <th>Phone</th>
        <th>Car Model</th>
        <th>Service Type</th>
        <th>Date</th>
        <th>Time</th>
    </tr>

<?php
// Connect to MySQL
$conn = new mysqli("localhost", "root", "your_password", "your_database");

// Check connection
if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Fetch appointments
$sql = "SELECT id, name, phone, car_model, service_type, service_date, service_time FROM appointments ORDER BY id DESC";
$result = $conn->query($sql);

if ($result->num_rows > 0) {
    while($row = $result->fetch_assoc()) {
        echo "<tr>
            <td>".$row["id"]."</td>
            <td>".$row["name"]."</td>
            <td>".$row["phone"]."</td>
            <td>".$row["car_model"]."</td>
            <td>".$row["service_type"]."</td>
            <td>".$row["service_date"]."</td>
            <td>".$row["service_time"]."</td>
        </tr>";
    }
} else {ś
    echo "<tr><td colspan='7'>No appointments yet</td></tr>";
}

$conn->close();
?>
</table>

</body>
</html>
