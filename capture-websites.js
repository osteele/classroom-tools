#!/usr/bin/env node
const captureWebsite = require("capture-website");
const fs = require("fs");
const argv = require("yargs").argv;
const ora = require("ora");
const path = require("path");
const process = require("process");

const OUTDIR = "screenshots";
const APP_URL_LABEL = "Heroku URL";

function readCsv(fname) {
    const rows = fs
        .readFileSync(fname, "utf-8")
        .split("\n")
        .map(line => line.trim("\n").split(","));
    const header = rows.shift().map(s => s.toLowerCase());
    const userNameIndex = 0;
    const urlIndex = header.indexOf(APP_URL_LABEL.toLowerCase());
    if (urlIndex < 0) {
        console.error(`Error: no header ${APP_URL_LABEL}`);
        process.exit(1);
    }
    return rows
        .map(fields => {
            const name = fields[userNameIndex];
            const url = fields[urlIndex];
            return { name, url };
        })
        .filter(({ url }) => url);
}

async function capturePages(entries, options) {
    const outdir = options.out || OUTDIR;
    const device = options.emulateDevice || "MacBook Pro";
    let suffix = options.emulateDevice ? `-${options.emulateDevice.toLowerCase().replace(/ /g, "-")}` : "";
    const message = `Capturing ${entries.length} pages for ${device}`;
    const spinner = ora(message).start();
    let promises = entries.map(({ name, url }) => {
        const filename = path.join(outdir, `${name}${suffix || ""}.png`);
        // console.log(`Capturing ${url} to ${filename}`);
        return captureWebsite.file(url, filename, { overwrite: true, ...options });
    });
    await Promise.all(promises);
    spinner.succeed(message.replace(/ing/, "ed"));
}

async function main({ _: files, user, url, out }) {
    const records = files.flatMap(readCsv);
    if (user) {
        records.push({ name: user, url: url || "http://localhost:3000" });
    }
    await capturePages(records, { width: 1280, height: 800, out }); // MacBook
    await capturePages(records, { emulateDevice: "iPhone 8", out });
}

(async () => await main(argv))();
