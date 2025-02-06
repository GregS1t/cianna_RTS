// server.js
// version 4
// Author: Grégory Sainton
// Date: 2025-01-25
// Purpose: Express Server to process XML, load FITS files and then processs 
//          them with YOLO-CIANNA neural network and return the results in 
//          a CSV file to the clients



const express = require("express");
const fs = require("fs");                   // to manage files
const path = require("path");
const multer = require("multer");           // to manage file uploads
const { spawn } = require("child_process"); // to run Python scripts
const { v4: uuidv4 } = require("uuid");     // to generate unique IDs

const app = express();
const port = 3000;

// Current directory
const CURRENT_DIR = __dirname;
// Output directory for CSV files
const OUTPUT_DIR = path.join(__dirname, "output");
if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR);
}

// Absolute path to the Python script
const PYTHON_CODE_DIR = path.join(__dirname, "python_code");
if (!fs.existsSync(PYTHON_CODE_DIR)) {
    fs.mkdirSync(PYTHON_CODE_DIR);
}
const pythonFilePath = path.join(PYTHON_CODE_DIR, "process_xml.py");

const YOLO_CODE_DIR = path.join(__dirname, "yolo_cianna_detect");
const yoloFilePath = path.join(YOLO_CODE_DIR, "code", "YC_RTS_detect.py");

app.use(express.text({ type: "application/xml" }));
app.use('/models', express.static(path.join(__dirname, 'models')));

const upload = multer({ dest: 'upload/' });


let jobs = {};

// Endpoint pour recevoir le fichier XML et lancer le traitement asynchrone
app.post("/upload", upload.fields([{ name: 'xml', maxCount: 1 }, { name: 'fits', maxCount: 1 }]), (req, res) => {
    const process_id = uuidv4();
    jobs[process_id] = { status: "PROCESSING", predFile: null, fitsFile: null };


    if (!req.files || !req.files.xml || req.files.xml.length === 0) {
        return res.status(400).json({ error: "SERVER: XML file is missing." });
    }
    if (!req.files.fits || req.files.fits.length === 0) {
        return res.status(400).json({ error: "SERVER: FITS file is missing." });
    }

    const xmlFileUploaded = req.files.xml[0];
    const fitsFileUploaded = req.files.fits[0];

    const xmlFilePath = path.join(__dirname, "upload", `temp_${process_id}.xml`);
    const fitsFilePath = path.join(__dirname, "images", `fits_${process_id}.fits`);

    try {
        fs.renameSync(xmlFileUploaded.path, xmlFilePath);
        fs.renameSync(fitsFileUploaded.path, fitsFilePath);

        jobs[process_id].fitsFile = fitsFilePath;
    } catch (err) {
        return res.status(500).json({ error: "Error during upload of the files." });
    }

    // Path to the output CSV file
    const prediction_file = `./fwd_res/net0_rts_`+process_id+`.dat`;
    const outputPredPath = path.join(CURRENT_DIR, prediction_file);
    // console.log("Output prediction file path: ", outputPredPath);
    
    // console.log("FITS file path: ", fitsFilePath);
    //
    // Check if the FITS file is valid
    //
    const pythonFITSCheck = path.join(PYTHON_CODE_DIR, "verify_fits.py");
    const verifyFITSProcess = spawn("python3", [pythonFITSCheck,  fitsFilePath]);

    verifyFITSProcess.stdout.on("data", (data) => {
        console.log(`FITS verification stdout: ${data.toString()}`);
    });
    verifyFITSProcess.stderr.on("data", (data) => {
        console.error(`FITS verification stderr: ${data.toString()}`);
    });

    verifyFITSProcess.on("close", (code) => {
        if (code !== 0) {
            //console.error(`FITS file verification failed for job ${process_id} with exit code ${code}`);
            // Optionally update job status and remove saved files if validation fails
            jobs[process_id].status = "ERROR";
            return res.status(400).json({ error: "FITS file verification failed." });
        }
        
        // Execute 
        const pythonYOLO = spawn("python3", [yoloFilePath, xmlFilePath, fitsFilePath, process_id]);

        pythonYOLO.stdout.on("data", (data) => {
            console.log(`Job ${process_id} - stdout: ${data.toString()}`);
        });
        pythonYOLO.stderr.on("data", (data) => {
            console.error(`Job ${process_id} - stderr: ${data.toString()}`);
        });

        pythonYOLO.on("close", (code) => {
            if (code === 0) {
                console.log(`Job ${process_id} terminated with success.`);
                jobs[process_id].status = "COMPLETED";
                jobs[process_id].predFile = outputPredPath;
            } else {
                console.error(`Job ${process_id} failed with code ${code}`);
                jobs[process_id].status = "ERROR";
            }
            // Remove the XML file
            //fs.unlink(xmlFilePath, (err) => {
            //    if (err) console.error(`Erreur during suppression of ${xmlFilePath}:`, err);
            //});
        });

        res.status(202).json({ process_id });
    });
});

// Endpoint to check the status of a job
app.get("/status/:process_id", (req, res) => {
    const process_id = req.params.process_id;
    if (jobs[process_id]) {
        res.json({ status: jobs[process_id].status });
    } else {
        res.status(404).json({ status: "ERROR", message: "Job not found" });
    }
});

// Endpoint pour télécharger le fichier CSV une fois le traitement terminé
app.get("/download/:process_id", (req, res) => {
    const process_id = req.params.process_id;
    const outputPredPath = path.join(CURRENT_DIR, `net0_rts_${process_id}.dat`);
    console.log("Output prediction file to push: ", outputPredPath);
    if (jobs[process_id] && jobs[process_id].status === "COMPLETED") {
        res.download(jobs[process_id].predFile, outputPredPath, (err) => {
            if (err) {
                res.status(500).json({ status: "ERROR", message: "Download error" });
            } else {
                console.log(`Prediction boxes file downloaded for job ${process_id}`);
            }
        });
    } else {
        res.status(404).json({ status: "ERROR", message: "File not found" });
    }
});

app.listen(port, () => {
    console.log(`Server listening:  http://127.0.0.1:${port}`);
});
