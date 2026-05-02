const display = document.getElementById("display");

function append(value) {
    display.value += value;
}

function backspace() {
    display.value = display.value.slice(0, -1);
}

function clearDisplay() {
    display.value = "";
}

// Convert degrees to radians
function degToRad(deg) {
    return deg * Math.PI / 180;
}

function calculate() {
    try {
        let expr = display.value;

        // Handle trig functions in degrees
        expr = expr.replace(/sin\(([^)]+)\)/g, (_, val) =>
            Math.sin(degToRad(Number(val)))
        );

        expr = expr.replace(/cos\(([^)]+)\)/g, (_, val) =>
            Math.cos(degToRad(Number(val)))
        );

        expr = expr.replace(/tan\(([^)]+)\)/g, (_, val) =>
            Math.tan(degToRad(Number(val)))
        );

        // Other scientific functions
        expr = expr.replace(/sqrt\(([^)]+)\)/g, (_, val) =>
            Math.sqrt(Number(val))
        );

        expr = expr.replace(/log\(([^)]+)\)/g, (_, val) =>
            Math.log10(Number(val))
        );

        expr = expr.replace(/ln\(([^)]+)\)/g, (_, val) =>
            Math.log(Number(val))
        );

        // Constants
        expr = expr.replace(/π/g, Math.PI);

        // Powers
        expr = expr.replace(/\^/g, "**");

        // Final evaluation
        const result = Function('"use strict"; return (' + expr + ')')();

        display.value = result;

    } catch (err) {
        display.value = "Error";
    }
}
