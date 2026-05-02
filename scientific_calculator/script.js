const display = document.getElementById("display");

function append(val) {
    display.value += val;
}

function clearDisplay() {
    display.value = "";
}

function calculate() {
    try {
        display.value = Function("return " + display.value)();
    } catch {
        display.value = "Error";
    }
}
