const titleText = "SUDOKU 2.O THE NUMBER PLACE";
const storyText = "Sudoku's roots trace back to 18th-century Swiss mathematician Leonhard Euler's 'Latin Squares.' The modern puzzle, initially called 'Number Place,' was invented by American architect Howard Garns in 1979 and published in Dell Magazines. It gained widespread popularity when introduced in Japan in 1984 by Nikoli, who renamed it 'Sudoku' (meaning 'single number'). The puzzle truly exploded globally in the early 2000s after being featured in British newspapers, becoming a worldwide phenomenon enjoyed by millions.";

let music = document.getElementById('bg-music');
let storyTimer;

// Handle Initial Start
window.onload = () => {
    // Wait 2 seconds, then start Title
    setTimeout(() => {
        typeWriter("title-container", titleText, 200, () => {
            // Wait 1 second after title finishes then go to story
            setTimeout(() => goToPage(2), 1500);
        });
    }, 2000);
    
    // Play music on first interaction
    window.addEventListener('mousedown', () => music.play(), { once: true });
};

// Generic Typewriter Function
function typeWriter(id, text, speed, callback) {
    let i = 0;
    const el = document.getElementById(id);
    el.innerHTML = "";
    
    let interval = setInterval(() => {
        el.innerHTML += text.charAt(i);
        i++;
        if (i >= text.length) {
            clearInterval(interval);
            if(callback) callback();
        }
    }, speed);
    
    return interval; // Return so we can clear it on SKIP
}

function goToPage(num) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const nextPage = document.getElementById(`page${num}`);
    nextPage.classList.add('active');

    if (num === 2) {
        // Reset story and start typing at 0.05s (50ms)
        document.getElementById('story-text').innerHTML = "";
        storyTimer = typeWriter("story-text", storyText, 50, showNext);
    }
}

function skipStory() {
    clearInterval(storyTimer);
    document.getElementById('story-text').innerHTML = storyText;
    showNext();
}

function showNext() {
    document.getElementById('skip-btn').classList.add('hidden');
    document.getElementById('next-to-p3').classList.remove('hidden');
}

function validateLanguage() {
    const selection = document.getElementById('language-picker').value;
    if (selection === "") {
        alert("Please Choose the Language First");
    } else {
        alert("Success! Entering Page 4...");
    }
}