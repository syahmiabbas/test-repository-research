{javascript}
const express = require('express');
const nodemailer = require('nodemailer');
const bodyParser = require('body-parser');
const cors = require('cors');
require('dotenv').config(); // Load environment variables
const app = express();
const PORT = 3000;

app.use(cors()); // Enable CORS
app.use(bodyParser.json());

let users = []; // In-memory user storage for demonstration

app.post('/api/register', (req, res) => {
    const { username, email } = req.body;
    if (!username || !email) {
        return res.status(400).json({ success: false, message: 'Invalid input' });
    }

    const confirmationLink = `http://localhost:${PORT}/confirm?email=${email}`;
    sendConfirmationEmail(email, confirmationLink)
        .then(() => {
            users.push({ username, email, confirmed: false });
            res.json({ success: true });
        })
        .catch(error => {
            console.error(error);
            res.status(500).json({ success: false, message: 'Failed to send confirmation email.' });
        });
});

function sendConfirmationEmail(email, link) {
    return new Promise((resolve, reject) => {
        const transporter = nodemailer.createTransport({
            service: 'gmail',
            auth: {
                user: process.env.EMAIL, // Use environment variable
                pass: process.env.EMAIL_PASSWORD // Use environment variable
            }
        });

        const mailOptions = {
            from: process.env.EMAIL,
            to: email,
            subject: 'Please confirm your registration',
            text: `Click this link to confirm your registration: ${link}`
        };

        transporter.sendMail(mailOptions, (error, info) => {
            if (error) {
                return reject(error);
            }
            console.log('Email sent: ' + info.response);
            resolve();
        });
    });
}

app.get('/confirm', (req, res) => {
    const { email } = req.query;
    const user = users.find(u => u.email === email);
    if (user) {
        user.confirmed = true;
        res.send('Email confirmed! You can now log in.');
    } else {
        res.send('Invalid confirmation link.');
    }
});

app.post('/api/login', (req, res) => {
    const { email } = req.body;
    const user = users.find(u => u.email === email && u.confirmed);
    if (user) {
        res.json({ success: true, message: 'Login successful!' });
    } else {
        res.status(401).json({ success: false, message: 'Authentication failed.' });
    }
});

app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});
