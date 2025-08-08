const socketChat = io();

const btnSendMessage = document.getElementById('btnSendMessage');
const chatBody = document.getElementById("chatBody");
const chatInput = document.getElementById("chatInput");
socketChat.on("connect", () => {
    console.log("Conectado al namespace /chat");
    // Enviar un mensaje al servidor
    const username = "WEB";
    socketChat.emit("message", {
        msg: "Cliente Conectado",
        username: username,
    });
});

socketChat.on("disconnect", data => {
    console.log("Desconectado del namespace /chat");
    // Add user message
    const username = "WEB";
    const sentMessage = document.createElement("div");
    sentMessage.classList.add("message", "sent");
    sentMessage.textContent = data.msg;
    chatBody.appendChild(sentMessage);
    socketChat.emit("message", {
        username: username,
        msg: "Cliente Desconectado"
    });
    // Clear input
    chatInput.value = "";
    // Scroll to bottom
    chatBody.scrollTop = chatBody.scrollHeight;
});
const message_pag = (message, new_class, tiempo) => {
    const enviado = document.getElementById("datos_message");
    const get_class = enviado.getAttribute("class");
    const set_class = get_class + " " + new_class;
    enviado.setAttribute("class", set_class);
    const nodes = enviado.childNodes[5];
    nodes.innerText = tiempo;
    const contenido = document.getElementById("contenido");
    contenido.innerText = message;
    toastLiveExample.append(contenido);
    const toastBootstrap = bootstrap.Toast.getOrCreateInstance(toastLiveExample);
    toastBootstrap.show();
};
socketChat.on("message", function (arg) {
    const row_id = JSON.parse(JSON.stringify(arg));
    console.log("DATA", row_id);
    const message = row_id.msg + " " + row_id.username;
    const tiempo = row_id.enviado;
    const new_class = "bg-success-subtle";
    message_pag(message, new_class, tiempo);
});
btnSendMessage.addEventListener("click", e => {
    e.preventDefault();
    debugger
    const messageText = chatInput.value.trim();
    const username = "WEB";
    if (messageText === "") return;

    // Add sent message
    const sentMessage = document.createElement("div");
    sentMessage.classList.add("message", "sent");
    sentMessage.textContent = messageText;
    chatBody.appendChild(sentMessage);
    socketChat.emit("message", { username: username, msg: messageText });
    // Clear input
    chatInput.value = "";

    // Scroll to the bottom
    chatBody.scrollTop = chatBody.scrollHeight;
});
// Allow sending messages with Enter key
chatInput.addEventListener("keypress", e => {
    if (e.key === "Enter") {
        e.preventDefault();
        const messageText = chatInput.value.trim();
        const username = "WEB";
        if (messageText === "") return;

        // Add sent message
        const sentMessage = document.createElement("div");
        sentMessage.classList.add("message", "sent");
        sentMessage.textContent = messageText;
        chatBody.appendChild(sentMessage);
        socketChat.emit("message", {
            username: username,
            msg: messageText
        });
        // Clear input
        chatInput.value = "";

        // Scroll to the bottom
        chatBody.scrollTop = chatBody.scrollHeight;
    }
});