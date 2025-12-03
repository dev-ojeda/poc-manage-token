export function openChat(rol) {
    const boton = document.getElementById("chatToggle");
    switch (rol) {
        case "Admin":
            boton.style.backgroundColor = "#ff6a00";
            boton.disabled = false;
            boton.innerText = "💬 Admin";
            break;
        case "User":
            boton.style.backgroundColor = "#00ff21";
            boton.disabled = false;
            boton.innerText = "💬 User";
            break;
        default:
            boton.style.backgroundColor = "#ccc";
            boton.disabled = true;
            boton.innerText = "Chat deshabilitado";
    }
}
