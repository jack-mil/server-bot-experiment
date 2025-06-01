const source = new EventSource("/stream/listen");

// source.onopen = () => console.log('Connection requested')

source.onmessage = function (event) {
    console.log(event);
}

source.addEventListener("new_msg", displayEvent);

function displayEvent(event) {
    const li = document.createElement("li");
    const a = document.createElement("a");
    const list = document.getElementById("events");

    const dataObj = JSON.parse(event.data);
    a.href = dataObj.url;
    const text = document.createTextNode(`${dataObj.date}${((dataObj.message)) ? " -- " + dataObj.message : ""}`);
    a.appendChild(text);
    li.appendChild(a);
    list.appendChild(li);
}