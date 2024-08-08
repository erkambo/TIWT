const openBtn = document.getElementById("goalbutton");
const closeBtn = document.getElementById("closegoal");
const goal = document.getElementById("newgoal");

openBtn.addEventListener("click", () => {
    goal.classList.add("open");
});

closeBtn.addEventListener("click", () => {
    goal.classList.remove("open");
});