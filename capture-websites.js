#!/usr/bin/env node
const captureWebsite = require("capture-website");
const fs = require("fs");

const entries = fs
    .readFileSync("untracked/final-projects.csv", "utf-8")
    .split("\n")
    .slice(1)
    .map(line => {
        const [name, url] = line.trim().split(",");
        return { name, url };
    })
    .filter(({ url }) => url);

const exceptions = [{ name: "user", url: "http://localhost:3000" }];

function capturePages(entries, options) {
    let suffix = options.emulateDevice ? `-${options.emulateDevice.toLowerCase().replace(/ /g, "-")}` : "";
    let promises = entries.map(({ name, url }) => {
        const filename = `snapshots/${name}${suffix || ""}.png`;
        return captureWebsite.file(url, filename, { overwrite: true, ...options });
    });
    return Promise.all(promises);
}

(async entries => {
    await capturePages(entries, { width: 1280, height: 800 }); // MacBook
    await capturePages(entries, { emulateDevice: "iPhone 8" }); // MacBook
})(exceptions);
