"""Builds content/jamb_starter_questions.json — ORIGINAL JAMB-style practice questions written for Kwado.

These are not official JAMB past questions. Every row imports as a *draft*: a human must verify the answer
and a second reviewer must publish it (Admin → Question bank).

Each entry: (difficulty 1-3, question, correct option, [three wrong options], explanation).
The correct option's position (A–D) is spread deterministically so answers aren't always the same letter.

    python content/build_jamb_starter.py      # rewrites the JSON next to this file
"""
import hashlib
import json
from pathlib import Path

SOURCE = "Kwado original (JAMB-style practice, not an official past question)"

# subject name → ID on the production database (as listed in Django admin). The importer matches on the
# name first, so the file still works if IDs differ on another database.
SUBJECT_IDS = {
    "Agricultural Science": 28, "Arabic": 19, "Biology": 27, "Chemistry": 26, "Christian Religious Studies": 35,
    "Civic Education": 37, "Commerce": 30, "Computer Studies": 13, "Economics": 29, "English Language": 23,
    "Financial Accounting": 31, "Fine Art": 16, "French": 18, "Geography": 34, "Government": 32, "Hausa": 20,
    "History": 12, "Home Economics": 14, "Igbo": 21, "Islamic Studies": 36, "Literature in English": 33,
    "Mathematics": 24, "Music": 17, "Physical and Health Education": 15, "Physics": 25, "Yoruba": 22,
}

Q = {
    "English Language": [
        (1, "Choose the option that best completes the sentence: Neither the principal nor the teachers ___ present at the meeting.", "were", ["was", "is", "has been"], "With 'neither … nor', the verb agrees with the nearer subject. 'Teachers' is plural, so 'were'."),
        (1, "Choose the option that best completes the sentence: The furniture in the new hall ___ very expensive.", "is", ["are", "were", "have been"], "'Furniture' is an uncountable noun and takes a singular verb."),
        (2, "Choose the word nearest in meaning to the word in italics: The witness gave a *lucid* account of the accident.", "clear", ["confused", "brief", "false"], "'Lucid' means expressed clearly and easy to understand."),
        (2, "Choose the word opposite in meaning to the word in italics: Tunde is known for his *generosity*.", "meanness", ["kindness", "wealth", "humility"], "Generosity is readiness to give freely; its opposite is meanness (stinginess)."),
        (1, "Choose the correctly spelt word.", "embarrass", ["embarass", "emmbarrass", "embarras"], "'Embarrass' has a double 'r' and a double 's'."),
        (2, "Choose the option that best completes the sentence: The students were warned to desist ___ noise-making.", "from", ["on", "in", "of"], "'Desist' is followed by the preposition 'from'."),
        (2, "Choose the option that best explains the idiom: Chika *let the cat out of the bag* at the party.", "revealed a secret", ["caused confusion", "arrived late", "lost her temper"], "To 'let the cat out of the bag' is to reveal a secret by accident."),
        (3, "Choose the option that best completes the sentence: Hardly had we arrived ___ the rain started.", "when", ["than", "then", "before"], "'Hardly … when' is the correct correlative pair. 'Than' goes with 'no sooner'."),
        (2, "Choose the option with a different vowel sound from the others.", "cut", ["heart", "card", "calm"], "'Heart', 'card' and 'calm' have the long vowel /ɑː/; 'cut' has the short vowel /ʌ/."),
        (3, "Which syllable carries the primary stress in the word 'photographer'?", "the second syllable (-to-)", ["the first syllable (pho-)", "the third syllable (-gra-)", "the fourth syllable (-pher)"], "In 'photographer' the stress falls on the second syllable: pho-TO-gra-pher."),
    ],
    "Mathematics": [
        (1, "Evaluate $\\log_{10} 8 + \\log_{10} 125$.", "3", ["2", "133", "1000"], "$\\log_{10} 8 + \\log_{10} 125 = \\log_{10}(8 \\times 125) = \\log_{10} 1000 = 3$."),
        (1, "Solve for $x$: $2x - 7 = 3x + 5$.", "$-12$", ["$12$", "$-2$", "$2$"], "Subtract $2x$ from both sides: $-7 = x + 5$, so $x = -12$."),
        (1, "Find the roots of $x^2 - 5x + 6 = 0$.", "2 and 3", ["−2 and −3", "1 and 6", "−1 and 6"], "$x^2 - 5x + 6 = (x - 2)(x - 3) = 0$, so $x = 2$ or $x = 3$."),
        (2, "Convert $101101_2$ to a number in base ten.", "45", ["43", "47", "53"], "$1\\times32 + 0\\times16 + 1\\times8 + 1\\times4 + 0\\times2 + 1\\times1 = 45$."),
        (1, "Find the mean of 4, 7, 9, 12 and 8.", "8", ["7", "9", "10"], "Sum = 40; mean = 40 ÷ 5 = 8."),
        (2, "Find the simple interest on ₦5,000 at 4% per annum for 3 years.", "₦600", ["₦200", "₦650", "₦6,000"], "$I = \\frac{PRT}{100} = \\frac{5000 \\times 4 \\times 3}{100} = 600$."),
        (1, "Find the gradient of the line joining $(2, 3)$ and $(6, 11)$.", "2", ["$\\frac{1}{2}$", "4", "−2"], "Gradient $= \\frac{11 - 3}{6 - 2} = \\frac{8}{4} = 2$."),
        (2, "Find the sum of the interior angles of a hexagon.", "720°", ["540°", "900°", "360°"], "Sum $= (n - 2) \\times 180° = 4 \\times 180° = 720°$."),
        (3, "Evaluate $\\int_0^2 3x^2\\,dx$.", "8", ["6", "12", "4"], "$\\int 3x^2\\,dx = x^3$; $2^3 - 0^3 = 8$."),
        (2, "If $y = 4x^3 - 2x$, find $\\frac{dy}{dx}$.", "$12x^2 - 2$", ["$12x^2 - 2x$", "$4x^2 - 2$", "$12x^3 - 2$"], "Differentiate term by term: $\\frac{d}{dx}(4x^3) = 12x^2$ and $\\frac{d}{dx}(2x) = 2$."),
    ],
    "Physics": [
        (1, "What is the SI unit of power?", "watt", ["joule", "newton", "pascal"], "Power is the rate of doing work, measured in watts (1 W = 1 J/s)."),
        (1, "A car starts from rest and reaches 20 m/s in 5 s with uniform acceleration. Find its acceleration.", "4 m/s²", ["100 m/s²", "0.25 m/s²", "25 m/s²"], "$a = \\frac{v - u}{t} = \\frac{20 - 0}{5} = 4$ m/s²."),
        (1, "Find the kinetic energy of a 2 kg body moving at 3 m/s.", "9 J", ["6 J", "18 J", "3 J"], "$KE = \\frac{1}{2}mv^2 = \\frac{1}{2} \\times 2 \\times 3^2 = 9$ J."),
        (2, "Resistors of 6 Ω and 3 Ω are connected in parallel. Find the effective resistance.", "2 Ω", ["9 Ω", "4.5 Ω", "0.5 Ω"], "$\\frac{1}{R} = \\frac{1}{6} + \\frac{1}{3} = \\frac{1}{2}$, so $R = 2$ Ω."),
        (1, "A wave has a frequency of 50 Hz and a wavelength of 2 m. Find its speed.", "100 m/s", ["25 m/s", "52 m/s", "0.04 m/s"], "$v = f\\lambda = 50 \\times 2 = 100$ m/s."),
        (1, "Which of the following is a scalar quantity?", "speed", ["velocity", "force", "displacement"], "Speed has magnitude only; the others also have direction, so they are vectors."),
        (2, "How much heat is needed to raise the temperature of 2 kg of water by 10 °C? (Specific heat capacity of water = 4200 J kg⁻¹ K⁻¹)", "84,000 J", ["42,000 J", "8,400 J", "840 J"], "$Q = mc\\Delta\\theta = 2 \\times 4200 \\times 10 = 84{,}000$ J."),
        (2, "An object is placed beyond 2F in front of a converging lens. The image formed is", "real, inverted and diminished", ["virtual, upright and magnified", "real, inverted and magnified", "virtual, inverted and diminished"], "Beyond 2F, a converging lens forms a real, inverted, diminished image between F and 2F on the other side."),
        (3, "A radioactive sample decays from 80 g to 10 g in 15 days. What is its half-life?", "5 days", ["7.5 days", "3 days", "15 days"], "80 → 40 → 20 → 10 g is three half-lives; 15 ÷ 3 = 5 days."),
        (1, "A force of 200 N acts on an area of 0.5 m². Find the pressure.", "400 Pa", ["100 Pa", "200.5 Pa", "0.0025 Pa"], "$P = \\frac{F}{A} = \\frac{200}{0.5} = 400$ Pa."),
    ],
    "Chemistry": [
        (1, "How many moles are there in 22 g of carbon(IV) oxide? (C = 12, O = 16)", "0.5 mol", ["1.0 mol", "2.0 mol", "0.25 mol"], "Molar mass of CO₂ = 12 + 32 = 44 g/mol; 22 ÷ 44 = 0.5 mol."),
        (2, "An element with electronic configuration 1s² 2s² 2p⁶ 3s² 3p¹ belongs to group", "III", ["I", "II", "V"], "It has 3 electrons in its outermost shell (3s² 3p¹), so it is in group III (aluminium)."),
        (1, "What is the pH of a neutral solution at 25 °C?", "7", ["0", "1", "14"], "At 25 °C a neutral solution has [H⁺] = 10⁻⁷ mol/dm³, so pH = 7."),
        (1, "Which gas turns lime water milky?", "carbon(IV) oxide", ["oxygen", "hydrogen", "nitrogen"], "CO₂ reacts with calcium hydroxide to form insoluble calcium carbonate, which makes the solution milky."),
        (2, "What is the oxidation number of manganese in KMnO₄?", "+7", ["+2", "+4", "+6"], "K = +1, 4 × O = −8, total 0: +1 + Mn − 8 = 0, so Mn = +7."),
        (1, "Which of the following is an alkane?", "C₃H₈", ["C₂H₄", "C₂H₂", "C₆H₆"], "Alkanes have the general formula CₙH₂ₙ₊₂; C₃H₈ (propane) fits."),
        (1, "Common salt can be recovered from its solution in water by", "evaporation", ["filtration", "sublimation", "decantation"], "Salt is dissolved, so heating to drive off the water leaves the salt behind."),
        (1, "Isotopes of an element differ in their number of", "neutrons", ["protons", "electrons", "atomic number"], "Isotopes have the same number of protons but different numbers of neutrons, hence different mass numbers."),
        (2, "Temporary hardness of water is caused by dissolved", "calcium hydrogencarbonate", ["calcium sulphate", "sodium chloride", "magnesium sulphate"], "Hydrogencarbonates cause temporary hardness, which boiling removes; sulphates cause permanent hardness."),
        (1, "The Avogadro constant is approximately", "6.02 × 10²³ mol⁻¹", ["6.02 × 10⁻²³ mol⁻¹", "3.01 × 10²³ mol⁻¹", "1.66 × 10⁻²⁴ mol⁻¹"], "One mole contains about 6.02 × 10²³ particles."),
    ],
    "Biology": [
        (1, "Which organelle is the site of aerobic respiration in a cell?", "mitochondrion", ["ribosome", "nucleus", "vacuole"], "Mitochondria carry out aerobic respiration and release most of the cell's energy."),
        (1, "In green plants, photosynthesis takes place in the", "chloroplast", ["mitochondrion", "cell wall", "nucleus"], "Chloroplasts contain chlorophyll, which traps light energy for photosynthesis."),
        (2, "Which blood vessel carries oxygenated blood from the lungs to the heart?", "pulmonary vein", ["pulmonary artery", "vena cava", "aorta"], "The pulmonary vein is the only vein that carries oxygenated blood; it returns blood from the lungs to the left atrium."),
        (1, "The enzyme in human saliva that begins starch digestion is", "salivary amylase (ptyalin)", ["pepsin", "lipase", "trypsin"], "Salivary amylase breaks starch down into maltose in the mouth."),
        (2, "Two heterozygous tall plants (Tt × Tt) are crossed. What is the expected ratio of tall to dwarf offspring?", "3 : 1", ["1 : 1", "1 : 2 : 1", "all tall"], "Offspring are TT, Tt, Tt and tt; three show the dominant tall trait and one is dwarf."),
        (1, "An organism that makes its own food from simple inorganic substances is called", "an autotroph", ["a heterotroph", "a saprophyte", "a parasite"], "Autotrophs, such as green plants, make their own food by photosynthesis or chemosynthesis."),
        (1, "Malaria is caused by", "Plasmodium", ["a virus", "Trypanosoma", "the Anopheles mosquito"], "Malaria is caused by the protozoan Plasmodium; the female Anopheles mosquito is only the vector."),
        (1, "The main function of xylem in plants is to", "transport water and mineral salts", ["transport manufactured food", "store starch", "carry out photosynthesis"], "Xylem carries water and dissolved mineral salts from the roots upwards; phloem carries food."),
        (2, "Insulin is produced by the", "pancreas", ["liver", "adrenal gland", "thyroid gland"], "The islets of Langerhans in the pancreas secrete insulin, which lowers blood glucose."),
        (1, "Which of the following is NOT a characteristic of living things?", "combustion", ["excretion", "irritability", "reproduction"], "Combustion is a chemical process, not a characteristic of life."),
    ],
    "Economics": [
        (1, "Opportunity cost is best described as", "the alternative forgone", ["the money price of a good", "the cost of production", "the total cost of all choices"], "Opportunity cost is the next best alternative given up when a choice is made."),
        (1, "Other things being equal, a rise in the price of a normal good leads to", "a fall in quantity demanded", ["a rise in quantity demanded", "a rise in demand", "no change in quantity demanded"], "The law of demand: price and quantity demanded move in opposite directions, ceteris paribus."),
        (2, "If the price of a good rises by 10% and the quantity demanded falls by 20%, the price elasticity of demand is", "2 (elastic)", ["0.5 (inelastic)", "1 (unitary)", "0 (perfectly inelastic)"], "PED = % change in quantity ÷ % change in price = 20 ÷ 10 = 2, which is greater than 1."),
        (1, "A market with a single seller and no close substitutes is", "a monopoly", ["an oligopoly", "perfect competition", "a duopoly"], "A monopoly has one seller of a product with no close substitutes."),
        (1, "Inflation is", "a persistent rise in the general price level", ["a fall in the general price level", "a rise in the price of one good", "an increase in output"], "Inflation is a sustained increase in the general level of prices."),
        (2, "Gross National Product (GNP) equals", "GDP plus net factor income from abroad", ["GDP minus depreciation", "GDP minus indirect taxes", "national income plus subsidies"], "GNP adds the net income residents earn from abroad to GDP."),
        (2, "The Central Bank of Nigeria acts as the lender of last resort to", "commercial banks", ["individual citizens", "foreign governments", "insurance companies"], "The central bank lends to commercial banks when they cannot get funds elsewhere."),
        (1, "The reward for land as a factor of production is", "rent", ["wages", "interest", "profit"], "Land earns rent, labour earns wages, capital earns interest and the entrepreneur earns profit."),
        (2, "The law of diminishing returns states that as more units of a variable factor are added to a fixed factor, eventually", "the marginal product falls", ["total product falls immediately", "average cost falls", "the fixed factor increases"], "After a point, each extra unit of the variable factor adds less to output than the one before."),
        (1, "Which of the following is a direct tax?", "personal income tax", ["value added tax", "import duty", "excise duty"], "A direct tax is paid by the person on whom it is levied; VAT and duties are indirect."),
    ],
    "Government": [
        (1, "The theory of separation of powers is associated with", "Baron de Montesquieu", ["John Locke", "A. V. Dicey", "Karl Marx"], "Montesquieu set out the separation of powers in The Spirit of the Laws (1748)."),
        (1, "Nigeria's federal legislature is called the", "National Assembly", ["House of Assembly", "Federal Executive Council", "Council of State"], "The National Assembly consists of the Senate and the House of Representatives."),
        (2, "How many members does the Nigerian Senate have?", "109", ["360", "36", "774"], "Three senators from each of the 36 states plus one from the FCT: 108 + 1 = 109."),
        (1, "The rule of law was popularised by", "A. V. Dicey", ["Jean Bodin", "Montesquieu", "Thomas Hobbes"], "A. V. Dicey set out the principles of the rule of law in 1885."),
        (1, "In a unitary system of government, power is concentrated in the", "central government", ["local governments", "regional governments", "traditional rulers"], "A unitary state has one central authority from which any lower bodies get their powers."),
        (1, "Nigeria became independent on", "1 October 1960", ["1 October 1963", "1 January 1914", "29 May 1999"], "Nigeria gained independence from Britain on 1 October 1960."),
        (2, "Nigeria became a republic in", "1963", ["1960", "1966", "1979"], "On 1 October 1963 Nigeria became a republic, with a Nigerian President replacing the British monarch as head of state."),
        (1, "Franchise means the right to", "vote", ["form a political party", "free speech", "own property"], "Franchise (suffrage) is the right to vote in elections."),
        (1, "The head of the judiciary in Nigeria is the", "Chief Justice of Nigeria", ["Attorney-General of the Federation", "President of the Court of Appeal", "Senate President"], "The Chief Justice of Nigeria heads the Supreme Court and the judiciary."),
        (2, "ECOWAS was established in", "1975", ["1963", "1960", "1999"], "The Treaty of Lagos established ECOWAS in May 1975."),
    ],
    "Literature in English": [
        (1, "A poem of fourteen lines is called", "a sonnet", ["an ode", "an elegy", "a ballad"], "A sonnet has fourteen lines, usually in iambic pentameter."),
        (1, "A story told by a character who uses 'I' is written in the", "first-person point of view", ["third-person point of view", "omniscient point of view", "second-person point of view"], "A first-person narrator tells the story from their own perspective using 'I'."),
        (1, "'Her voice was as sweet as honey' is an example of", "simile", ["metaphor", "personification", "hyperbole"], "A simile compares two things using 'like' or 'as'."),
        (1, "The character who opposes the main character in a story is the", "antagonist", ["protagonist", "narrator", "foil"], "The antagonist works against the protagonist."),
        (1, "The repetition of the same consonant sound at the start of nearby words is", "alliteration", ["assonance", "onomatopoeia", "rhyme"], "Example: 'Peter Piper picked…' repeats the /p/ sound."),
        (2, "A play in which the main character suffers a downfall, often through a personal flaw, is a", "tragedy", ["comedy", "farce", "melodrama"], "Tragedy traces the fall of a protagonist, often caused by a tragic flaw."),
        (1, "'I have told you a million times' is an example of", "hyperbole", ["litotes", "irony", "euphemism"], "Hyperbole is deliberate exaggeration for effect."),
        (2, "A speech in which a character alone on stage speaks their thoughts aloud is a", "soliloquy", ["monologue", "dialogue", "aside"], "In a soliloquy the character is alone and reveals inner thoughts to the audience."),
        (1, "An elegy is a poem that", "mourns the dead", ["celebrates a wedding", "tells a funny story", "praises nature"], "An elegy is a lament for someone who has died."),
        (2, "The time and place in which a story happens is its", "setting", ["plot", "theme", "climax"], "Setting is the when and where of a story."),
    ],
    "Geography": [
        (1, "The earth rotates once on its axis in about", "24 hours", ["365 days", "12 hours", "30 days"], "One rotation takes about 24 hours and causes day and night."),
        (2, "When it is 12 noon at Greenwich (0°), what is the local time at a place on longitude 45° E?", "3:00 p.m.", ["9:00 a.m.", "12:45 p.m.", "3:00 a.m."], "Each 15° of longitude is 1 hour; places east are ahead. 45 ÷ 15 = 3 hours ahead."),
        (2, "On a map of scale 1 : 50,000, a distance of 4 cm represents", "2 km", ["20 km", "0.2 km", "200 km"], "4 × 50,000 = 200,000 cm = 2,000 m = 2 km."),
        (1, "Which of the following is an igneous rock?", "granite", ["limestone", "sandstone", "marble"], "Granite forms from cooled magma; limestone and sandstone are sedimentary, marble is metamorphic."),
        (1, "The harmattan wind in Nigeria blows from the", "north-east", ["south-west", "south-east", "north-west"], "The harmattan is the dry, dusty north-east trade wind from the Sahara."),
        (1, "The line of latitude 0° is the", "Equator", ["Prime Meridian", "Tropic of Cancer", "Arctic Circle"], "The Equator is latitude 0°; the Prime Meridian is longitude 0°."),
        (1, "The Rivers Niger and Benue meet at", "Lokoja", ["Onitsha", "Jebba", "Makurdi"], "The confluence of the Niger and Benue is at Lokoja in Kogi State."),
        (1, "Most weather occurs in the layer of the atmosphere called the", "troposphere", ["stratosphere", "mesosphere", "thermosphere"], "The troposphere is the lowest layer and holds most water vapour, so weather happens there."),
        (2, "Contour lines drawn close together on a map indicate", "a steep slope", ["a gentle slope", "flat land", "a river valley floor"], "Closely spaced contours mean height changes quickly over a short distance."),
        (2, "A town has 200,000 people on 50 km² of land. Its population density is", "4,000 persons per km²", ["250 persons per km²", "10,000,000 persons per km²", "40 persons per km²"], "Density = population ÷ area = 200,000 ÷ 50 = 4,000 per km²."),
    ],
    "Commerce": [
        (1, "Which of the following is NOT an aid to trade?", "manufacturing", ["banking", "insurance", "transport"], "Aids to trade help the exchange of goods (banking, insurance, transport, advertising, warehousing); manufacturing is production."),
        (1, "A retailer sells goods mainly to", "final consumers", ["manufacturers", "wholesalers", "importers"], "The retailer is the last link in the chain of distribution."),
        (2, "The insurance principle that requires both parties to disclose all material facts is", "utmost good faith", ["indemnity", "subrogation", "contribution"], "Uberrimae fidei (utmost good faith) requires full disclosure of all material facts."),
        (2, "A bill of lading is a document used in", "sea transport", ["air transport", "rail transport", "road transport"], "It is a receipt and document of title for goods shipped by sea."),
        (1, "A sole proprietor's liability for the business's debts is", "unlimited", ["limited", "shared with shareholders", "covered by the government"], "A sole trader's personal assets can be used to pay business debts."),
        (2, "A crossed cheque can only be", "paid into a bank account", ["cashed over the counter", "used once a year", "issued by a company"], "Crossing a cheque means it must be paid into a bank account, not cashed."),
        (2, "Under a hire purchase agreement, ownership of the goods passes to the buyer", "after the last instalment is paid", ["when the first instalment is paid", "at the signing of the agreement", "never"], "The seller keeps ownership until the final instalment is paid."),
        (1, "Containerisation is mainly associated with", "transport", ["banking", "advertising", "insurance"], "Containerisation moves goods in standard containers across ships, trains and lorries."),
        (2, "Trade discount is usually given to", "encourage bulk buying by traders", ["encourage prompt payment", "penalise late payment", "reduce taxes"], "Trade discount is a reduction off list price for traders, often for buying in bulk; cash discount rewards prompt payment."),
        (1, "Commerce is best defined as", "trade and aids to trade", ["the production of goods", "buying only", "the work of government"], "Commerce covers trade (buying and selling) and the services that make it possible."),
    ],
    "Financial Accounting": [
        (1, "The accounting equation is", "Assets = Capital + Liabilities", ["Assets = Capital − Liabilities", "Capital = Assets + Liabilities", "Liabilities = Assets + Capital"], "What a business owns equals what it owes to the owner and to outsiders."),
        (1, "Under the double-entry principle, every debit entry has", "a corresponding credit entry", ["another debit entry", "no other entry", "a cash entry"], "Each transaction is recorded twice: a debit in one account and a credit in another."),
        (2, "A machine costs ₦100,000, has a residual value of ₦10,000 and a useful life of 5 years. Using the straight-line method, the annual depreciation is", "₦18,000", ["₦20,000", "₦22,000", "₦10,000"], "(100,000 − 10,000) ÷ 5 = ₦18,000 per year."),
        (1, "The main purpose of a trial balance is to", "check the arithmetical accuracy of the ledger", ["find the net profit", "show the financial position", "record cash transactions"], "Matching debit and credit totals shows the double entries balance."),
        (2, "Opening stock ₦5,000, purchases ₦20,000, closing stock ₦3,000. Find the cost of goods sold.", "₦22,000", ["₦28,000", "₦18,000", "₦25,000"], "Cost of goods sold = 5,000 + 20,000 − 3,000 = ₦22,000."),
        (1, "Sales ₦50,000 and cost of sales ₦32,000 give a gross profit of", "₦18,000", ["₦82,000", "₦32,000", "₦50,000"], "Gross profit = sales − cost of sales = 50,000 − 32,000 = ₦18,000."),
        (2, "A prepaid expense is shown in the statement of financial position as", "a current asset", ["a current liability", "a non-current asset", "capital"], "Payment made in advance gives the business a benefit to come, so it is a current asset."),
        (1, "Drawings by the owner reduce", "capital", ["liabilities", "sales", "expenses"], "Drawings are withdrawals for personal use, so they reduce the owner's capital."),
        (2, "In a bank reconciliation, cheques issued but not yet presented to the bank are called", "unpresented cheques", ["dishonoured cheques", "uncredited cheques", "standing orders"], "They are in the cash book but not yet on the bank statement."),
        (2, "Under the imprest system, the petty cashier is reimbursed", "the amount spent during the period", ["a fixed salary", "half of the float", "nothing"], "The float is restored by reimbursing exactly what was spent."),
    ],
    "Christian Religious Studies": [
        (1, "Who led the Israelites out of Egypt?", "Moses", ["Joshua", "Aaron", "Abraham"], "God called Moses to lead Israel out of Egypt (Exodus 3–14)."),
        (1, "Who was the first king of Israel?", "Saul", ["David", "Solomon", "Samuel"], "Samuel anointed Saul as Israel's first king (1 Samuel 10)."),
        (1, "Jesus was baptised in the River Jordan by", "John the Baptist", ["Peter", "Andrew", "John the apostle"], "Matthew 3:13–17."),
        (1, "Which disciple denied Jesus three times?", "Peter", ["Judas Iscariot", "Thomas", "John"], "Peter denied Jesus three times before the cock crowed (Luke 22:54–62)."),
        (1, "Saul (Paul) was converted on the road to", "Damascus", ["Jerusalem", "Antioch", "Emmaus"], "Acts 9:1–19."),
        (1, "Which prophet was swallowed by a great fish?", "Jonah", ["Elijah", "Jeremiah", "Amos"], "Jonah 1:17."),
        (2, "Which of the following is listed as a fruit of the Spirit in Galatians 5?", "self-control", ["wealth", "wisdom", "courage"], "Galatians 5:22–23 lists love, joy, peace, patience, kindness, goodness, faithfulness, gentleness and self-control."),
        (1, "Who interpreted Pharaoh's dreams of fat and thin cows?", "Joseph", ["Daniel", "Moses", "Jacob"], "Genesis 41."),
        (2, "On the day of Pentecost, the disciples", "were filled with the Holy Spirit", ["chose Matthias", "saw Jesus ascend", "were scattered from Jerusalem"], "Acts 2:1–4."),
        (2, "Elijah challenged the prophets of Baal on Mount", "Carmel", ["Sinai", "Zion", "Olives"], "1 Kings 18:19–40."),
    ],
    "Islamic Studies": [
        (1, "The first verses revealed to Prophet Muhammad (SAW) are in Surah", "al-Alaq", ["al-Fatihah", "al-Baqarah", "al-Ikhlas"], "Q96:1–5 (Iqra) were revealed first, in the cave of Hira."),
        (1, "How many surahs are in the Qur'an?", "114", ["99", "112", "124"], "The Qur'an has 114 surahs."),
        (1, "How many pillars of Islam are there?", "five", ["three", "six", "seven"], "Shahadah, Salat, Zakat, Sawm and Hajj."),
        (1, "Muslims fast during the month of", "Ramadan", ["Shawwal", "Muharram", "Rajab"], "Fasting in Ramadan is the fourth pillar of Islam."),
        (2, "The Hijrah from Makkah to Madinah took place in", "622 CE", ["570 CE", "610 CE", "632 CE"], "The Hijrah in 622 CE marks the start of the Islamic calendar."),
        (1, "The first Caliph after the Prophet (SAW) was", "Abu Bakr", ["Umar", "Uthman", "Ali"], "Abu Bakr as-Siddiq became the first caliph in 632 CE."),
        (1, "Zakat is", "obligatory alms", ["voluntary charity", "pilgrimage", "fasting"], "Zakat is compulsory alms on qualifying wealth; voluntary charity is sadaqah."),
        (1, "The opening chapter of the Qur'an is", "al-Fatihah", ["al-Nas", "al-Baqarah", "Yasin"], "Al-Fatihah is the first surah and is recited in every rak'ah."),
        (2, "Laylat al-Qadr (the Night of Power) falls in the month of", "Ramadan", ["Dhul-Hijjah", "Sha'ban", "Rabi' al-Awwal"], "Q97 and hadith place it in the last ten nights of Ramadan."),
        (1, "How many obligatory daily prayers are there?", "five", ["three", "four", "six"], "Fajr, Zuhr, Asr, Maghrib and Isha."),
    ],
    "History": [
        (1, "The Northern and Southern Protectorates of Nigeria were amalgamated in 1914 by", "Lord Lugard", ["Sir Arthur Richards", "Sir Hugh Clifford", "Sir John Macpherson"], "Frederick Lugard carried out the amalgamation in 1914."),
        (1, "The Sokoto Caliphate was founded following the jihad led by", "Usman dan Fodio", ["Muhammad Bello", "El-Kanemi", "Mai Idris Alooma"], "Usman dan Fodio launched the jihad in 1804."),
        (2, "Nigeria's seat of government moved officially from Lagos to Abuja in", "1991", ["1976", "1983", "1999"], "The move was made official on 12 December 1991."),
        (1, "The traditional ruler of the Benin kingdom is called the", "Oba", ["Alaafin", "Emir", "Obi"], "The Oba of Benin; the Alaafin rules Oyo."),
        (2, "In the old Oyo Empire, the council of kingmakers was the", "Oyo Mesi", ["Ogboni", "Ilari", "Ekpe"], "The Oyo Mesi, led by the Bashorun, checked the Alaafin's power."),
        (1, "Nigeria's first Prime Minister was", "Sir Abubakar Tafawa Balewa", ["Dr Nnamdi Azikiwe", "Chief Obafemi Awolowo", "Sir Ahmadu Bello"], "Balewa was Prime Minister from 1957 (federal) through independence until 1966."),
        (1, "The ruler of the Kanem-Bornu Empire was known as the", "Mai", ["Sarki", "Oba", "Eze"], "Kanem-Bornu rulers bore the title Mai."),
        (1, "The Nigerian Civil War lasted from", "1967 to 1970", ["1960 to 1963", "1966 to 1967", "1970 to 1975"], "It began in July 1967 and ended in January 1970."),
        (2, "The Aro oracle known as the 'Long Juju' was", "Ibini Ukpabi", ["Ogun", "Amadioha", "Sango"], "Ibini Ukpabi at Arochukwu was central to Aro influence in the hinterland."),
        (2, "The system of governing through traditional rulers that the British used in Northern Nigeria was", "indirect rule", ["direct rule", "assimilation", "association"], "Lugard ruled through emirs and existing institutions: indirect rule."),
    ],
    "Agricultural Science": [
        (1, "Which soil type holds the most water?", "clay", ["sand", "gravel", "sandy loam"], "Clay's fine particles and tiny pores retain much more water."),
        (1, "Which of the following is a leguminous crop?", "cowpea", ["maize", "yam", "cassava"], "Cowpea is a legume; its root nodules fix nitrogen."),
        (1, "Which of the following is a ruminant?", "cattle", ["pig", "rabbit", "chicken"], "Cattle have a four-chambered stomach and chew the cud."),
        (1, "In NPK fertiliser, N stands for", "nitrogen", ["neon", "nickel", "sodium"], "N = nitrogen, P = phosphorus, K = potassium."),
        (2, "The gestation period of a cow is about", "283 days", ["114 days", "150 days", "31 days"], "About 283 days (roughly 9 months); 114 days is the pig's and 31 days the rabbit's."),
        (1, "Covering the soil surface with dry grass or leaves to conserve moisture is called", "mulching", ["ridging", "pruning", "thinning"], "Mulch reduces evaporation and controls weeds."),
        (1, "Newcastle disease mainly affects", "poultry", ["cattle", "goats", "fish"], "Newcastle disease is a viral disease of birds, especially chickens."),
        (2, "Removing excess water from waterlogged soil is called", "drainage", ["irrigation", "leaching", "tillage"], "Drainage removes excess water; irrigation adds water."),
        (2, "Which of the following is a cattle breed indigenous to Nigeria?", "White Fulani", ["Friesian", "Jersey", "Large White"], "White Fulani (Bunaji) is a Nigerian zebu breed; Friesian and Jersey are exotic; Large White is a pig."),
        (2, "A major benefit of crop rotation is that it", "helps maintain soil fertility", ["increases soil erosion", "removes the need for land", "makes all crops grow faster"], "Rotating crops with different needs, including legumes, maintains fertility and breaks pest cycles."),
    ],
    "Civic Education": [
        (1, "Freedom of expression is guaranteed in the 1999 Constitution of Nigeria as", "a fundamental human right", ["a directive principle", "a duty of citizens", "a state policy"], "Chapter IV of the 1999 Constitution (section 39)."),
        (1, "Nigerian citizenship may be acquired by birth, registration or", "naturalisation", ["employment", "marriage alone", "residence for one year"], "Chapter III of the 1999 Constitution."),
        (1, "The National Pledge begins with", "I pledge to Nigeria my country", ["Arise, O compatriots", "Nigeria, we hail thee", "O God of creation"], "'I pledge to Nigeria my country, to be faithful, loyal and honest…'"),
        (1, "Which agency fights economic and financial crimes in Nigeria?", "EFCC", ["NDLEA", "NAFDAC", "FRSC"], "The Economic and Financial Crimes Commission."),
        (1, "The agency that fights the trafficking of illegal drugs in Nigeria is", "NDLEA", ["NAPTIP", "EFCC", "NCC"], "The National Drug Law Enforcement Agency."),
        (1, "The agency responsible for fighting human trafficking in Nigeria is", "NAPTIP", ["NDLEA", "INEC", "NIMC"], "The National Agency for the Prohibition of Trafficking in Persons."),
        (1, "The minimum voting age in Nigeria is", "18 years", ["16 years", "21 years", "25 years"], "Citizens aged 18 and above may register and vote."),
        (1, "The rule of law means", "the supremacy of the law over everyone", ["rule by the military", "rule by the richest", "rule by traditional rulers"], "No one is above the law, and everyone is equal before it."),
        (2, "The fundamental human rights in the 1999 Constitution are in", "Chapter IV", ["Chapter II", "Chapter III", "Chapter VI"], "Chapter IV, sections 33–46."),
        (1, "A non-governmental organisation (NGO) is an example of", "a civil society organisation", ["an arm of government", "a political party", "a law court"], "NGOs are independent of government and part of civil society."),
    ],
    "Computer Studies": [
        (1, "Which part of a computer is called its 'brain'?", "CPU", ["monitor", "hard disk", "keyboard"], "The Central Processing Unit carries out instructions."),
        (1, "One byte is equal to", "8 bits", ["4 bits", "16 bits", "1024 bits"], "A byte is 8 binary digits."),
        (1, "Which of the following is an input device?", "keyboard", ["printer", "monitor", "speaker"], "A keyboard sends data into the computer; the others are output devices."),
        (2, "Which type of memory loses its contents when power is switched off?", "RAM", ["ROM", "hard disk", "flash drive"], "RAM is volatile; the others keep data without power."),
        (2, "What is 13 in binary?", "1101", ["1011", "1110", "1001"], "13 = 8 + 4 + 1 = 1101₂."),
        (1, "The World Wide Web was invented by", "Tim Berners-Lee", ["Bill Gates", "Charles Babbage", "Steve Jobs"], "Tim Berners-Lee proposed the Web in 1989."),
        (1, "Which of the following is an operating system?", "Linux", ["Microsoft Excel", "Adobe Photoshop", "Mozilla Firefox"], "Linux manages hardware and runs programs; the others are applications."),
        (2, "Which logic gate gives an output of 1 only when all its inputs are 1?", "AND", ["OR", "NOT", "NOR"], "AND outputs 1 only if every input is 1."),
        (1, "HTTP stands for", "HyperText Transfer Protocol", ["High Transfer Text Program", "HyperText Transmission Program", "Home Tool Transfer Protocol"], "The protocol used to transfer web pages."),
        (2, "Malicious software that attaches itself to files and spreads when they are run is a", "virus", ["firewall", "compiler", "browser"], "A virus copies itself into other programs or files."),
    ],
    "Home Economics": [
        (1, "The nutrient mainly needed for body building and repair is", "protein", ["carbohydrate", "fat", "water"], "Proteins build and repair body tissues."),
        (1, "Scurvy is caused by a lack of", "vitamin C", ["vitamin A", "vitamin D", "iron"], "Vitamin C deficiency causes scurvy (bleeding gums, poor healing)."),
        (1, "Kwashiorkor is caused mainly by a lack of", "protein", ["vitamin B", "iodine", "calcium"], "Kwashiorkor is a protein-deficiency disease of young children."),
        (1, "Rickets in children is caused by a lack of", "vitamin D", ["vitamin C", "vitamin K", "iodine"], "Vitamin D is needed to absorb calcium for strong bones."),
        (1, "Anaemia is commonly caused by a lack of", "iron", ["iodine", "vitamin A", "fat"], "Iron is needed to make haemoglobin."),
        (1, "Cooking food in hot oil is called", "frying", ["boiling", "steaming", "baking"], "Frying uses hot fat or oil."),
        (1, "Which fabric comes from a plant?", "cotton", ["wool", "silk", "nylon"], "Cotton is a plant fibre; wool and silk are animal fibres; nylon is synthetic."),
        (1, "A family made up of a father, mother and their children is", "a nuclear family", ["an extended family", "a polygamous family", "a single-parent family"], "A nuclear family is parents and their children."),
        (2, "Preserving food by removing its moisture is", "drying", ["canning", "freezing", "pickling"], "Drying removes water microbes need to grow."),
        (1, "Goitre is linked to a lack of", "iodine", ["iron", "calcium", "vitamin C"], "Iodine is needed by the thyroid gland."),
    ],
    "Physical and Health Education": [
        (1, "How many players does a football team have on the field?", "11", ["9", "7", "15"], "Each side fields eleven players."),
        (1, "How many players does a basketball team have on the court?", "5", ["6", "7", "11"], "Five players per side are on court."),
        (1, "How many players does a volleyball team have on the court?", "6", ["5", "7", "9"], "Six players per side."),
        (1, "The Olympic Games are held every", "4 years", ["2 years", "3 years", "5 years"], "The Summer Olympics are held every four years."),
        (2, "The official marathon distance is", "42.195 km", ["21.1 km", "40 km", "50 km"], "The marathon has been 42.195 km since 1921."),
        (2, "In first aid for sprains, RICE stands for", "Rest, Ice, Compression, Elevation", ["Run, Ice, Cool, Exercise", "Rest, Inject, Cover, Elevate", "Relax, Ice, Clean, Exercise"], "RICE limits swelling and pain."),
        (2, "The best first aid for a nosebleed is to", "lean forward and pinch the soft part of the nose", ["tilt the head backwards", "lie flat on the back", "blow the nose hard"], "Leaning forward stops blood running down the throat; pinching applies pressure."),
        (1, "Malaria is transmitted by the", "female Anopheles mosquito", ["housefly", "tsetse fly", "male Anopheles mosquito"], "Only the female Anopheles bites and transmits Plasmodium."),
        (2, "The large group of muscles at the front of the thigh is the", "quadriceps", ["hamstrings", "biceps", "triceps"], "The quadriceps straighten the knee."),
        (1, "A standard outdoor running track is", "400 m", ["200 m", "100 m", "800 m"], "One lap of a standard outdoor track is 400 m."),
    ],
    "Fine Art": [
        (1, "The primary colours in pigment are", "red, yellow and blue", ["red, green and blue", "orange, green and violet", "black, white and grey"], "In painting, red, yellow and blue cannot be mixed from other colours."),
        (1, "Mixing blue and yellow gives", "green", ["orange", "purple", "brown"], "Blue + yellow = green."),
        (2, "The complementary colour of red is", "green", ["blue", "yellow", "orange"], "Complementary colours sit opposite each other on the colour wheel."),
        (1, "Adding white to a colour produces a", "tint", ["shade", "tone", "hue"], "A tint is a colour + white; a shade is a colour + black."),
        (2, "The Nok culture is best known for its", "terracotta sculptures", ["bronze heads", "ivory masks", "stone monoliths"], "Nok terracottas are among the oldest sculptures in sub-Saharan Africa."),
        (2, "The Benin bronzes were made by the", "lost-wax (cire perdue) method", ["carving method", "weaving method", "coiling method"], "A wax model is covered in clay, melted out, then replaced with molten metal."),
        (1, "Adire is a resist-dyed cloth associated with the", "Yoruba", ["Hausa", "Tiv", "Efik"], "Adire is the indigo resist-dyed cloth of the Yoruba."),
        (2, "Uli body and wall painting is associated with the", "Igbo", ["Yoruba", "Nupe", "Kanuri"], "Uli is a traditional Igbo design art."),
        (2, "The technique of showing depth and distance on a flat surface is", "perspective", ["texture", "rhythm", "symmetry"], "Linear perspective makes distant objects smaller and lines converge."),
        (2, "The sculptor of the bronze 'Anyanwu' at the National Museum, Lagos, is", "Ben Enwonwu", ["Bruce Onobrakpeya", "Yusuf Grillo", "Uche Okeke"], "Ben Enwonwu created 'Anyanwu' (1955)."),
    ],
    "Music": [
        (1, "How many lines does a musical staff have?", "5", ["4", "6", "3"], "The staff (stave) has five lines and four spaces."),
        (1, "A semibreve is equal in value to", "4 crotchets", ["2 crotchets", "8 crotchets", "1 crotchet"], "Semibreve = 2 minims = 4 crotchets."),
        (1, "The treble clef is also called the", "G clef", ["F clef", "C clef", "bass clef"], "It curls around the G line."),
        (1, "The tempo marking 'allegro' means", "fast and lively", ["slowly", "very soft", "gradually slower"], "Allegro indicates a quick, lively tempo."),
        (1, "The dynamic marking 'forte' (f) means", "loud", ["soft", "fast", "slow"], "Forte means loud; piano (p) means soft."),
        (2, "The pattern of tones (T) and semitones (S) in a major scale is", "T T S T T T S", ["T S T T S T T", "T T T S T T S", "S T T T S T T"], "e.g. C D E F G A B C."),
        (2, "The interval from C up to G is a", "perfect fifth", ["major third", "perfect fourth", "major sixth"], "C–D–E–F–G spans five letter names and seven semitones."),
        (2, "Which major key has one sharp in its key signature?", "G major", ["D major", "F major", "C major"], "G major has F♯; D major has two sharps; F major has one flat."),
        (1, "The Yoruba 'talking drum' is called", "dùndún", ["ogene", "goje", "udu"], "The dùndún imitates the tones of spoken Yoruba."),
        (2, "The oratorio 'Messiah' was composed by", "George Frideric Handel", ["Johann Sebastian Bach", "Wolfgang Amadeus Mozart", "Ludwig van Beethoven"], "Handel composed Messiah in 1741."),
    ],
    "French": [
        (1, "Choisissez la bonne réponse : Je ___ étudiant.", "suis", ["es", "est", "sommes"], "Être: je suis, tu es, il est, nous sommes."),
        (1, "Le pluriel de « le cheval » est", "les chevaux", ["les chevals", "les chevaus", "les chevales"], "Most nouns in -al take -aux in the plural."),
        (2, "Choisissez la bonne réponse : Hier, nous ___ au marché.", "sommes allés", ["avons allé", "allons", "sommes allé"], "Aller takes être in the passé composé; the participle agrees with 'nous' (masculine plural)."),
        (1, "« I am hungry » se dit", "J'ai faim", ["Je suis faim", "J'ai soif", "Je suis fatigué"], "French uses avoir: j'ai faim."),
        (1, "Choisissez la bonne réponse : Comment ___-vous ?", "allez", ["allons", "vas", "va"], "Vous allez → Comment allez-vous ?"),
        (1, "Le féminin de « acteur » est", "actrice", ["acteuse", "acteure", "actresse"], "Nouns in -teur often become -trice."),
        (1, "« Il fait chaud » veut dire", "It is hot", ["It is cold", "It is raining", "It is windy"], "Weather expressions use il fait."),
        (1, "Choisissez la bonne réponse : Elle ___ ses devoirs chaque soir.", "fait", ["fais", "faisons", "font"], "Faire: je fais, tu fais, il/elle fait."),
        (1, "Le contraire de « grand » est", "petit", ["gros", "long", "haut"], "Grand (big/tall) ↔ petit (small)."),
        (1, "« The book is on the table » : Le livre est ___ la table.", "sur", ["sous", "dans", "devant"], "Sur = on; sous = under; dans = in; devant = in front of."),
    ],
    "Arabic": [
        (1, "What is the meaning of « كِتَاب »?", "book", ["pen", "house", "school"], "كِتَاب (kitāb) means book."),
        (1, "What is the plural of « قَلَم » (pen)?", "أَقْلَام", ["قَلَمَات", "قُلُوم", "قَلَمُون"], "قَلَم → أَقْلَام (aqlām)."),
        (1, "What is the meaning of « بَيْت »?", "house", ["door", "mosque", "road"], "بَيْت (bayt) means house."),
        (1, "What is the meaning of « مَدْرَسَة »?", "school", ["teacher", "student", "lesson"], "مَدْرَسَة (madrasah) means school."),
        (1, "Which word means 'teacher' (masculine)?", "مُدَرِّس", ["طَالِب", "مَكْتَب", "دَرْس"], "مُدَرِّس (mudarris) is a male teacher; طَالِب is a student."),
        (1, "What is « ثَلَاثَة » in English?", "three", ["two", "four", "five"], "ثَلَاثَة (thalāthah) = three."),
    ],
    "Hausa": [
        (1, "What does « Na gode » mean?", "Thank you", ["Good morning", "Welcome", "Goodbye"], "Na gode = thank you."),
        (1, "What is the Hausa number 'biyu'?", "two", ["one", "three", "four"], "ɗaya = 1, biyu = 2, uku = 3, huɗu = 4."),
        (1, "The Hausa word for 'water' is", "ruwa", ["abinci", "gida", "rana"], "Ruwa = water; abinci = food; gida = house; rana = sun/day."),
        (1, "Which greeting is commonly used for 'hello' in Hausa?", "Sannu", ["Na gode", "Sai an jima", "Barka da sallah"], "Sannu is the common greeting; sai an jima means 'see you later'."),
    ],
    "Igbo": [
        (1, "What does « Ụtụtụ ọma » mean?", "Good morning", ["Good night", "Thank you", "Welcome"], "Ụtụtụ ọma = good morning."),
        (1, "What is the Igbo number 'abụọ'?", "two", ["one", "three", "four"], "otu = 1, abụọ = 2, atọ = 3, anọ = 4."),
        (1, "« Nnọọ » means", "Welcome", ["Goodbye", "Sorry", "Thank you"], "Nnọọ is used to welcome someone."),
        (1, "The Igbo word for 'water' is", "mmiri", ["nri", "ụlọ", "anyanwụ"], "Mmiri = water; nri = food; ụlọ = house; anyanwụ = sun."),
    ],
    "Yoruba": [
        (1, "What does « Ẹ káàárọ̀ » mean?", "Good morning", ["Good evening", "Thank you", "Welcome"], "Ẹ káàárọ̀ is the respectful 'good morning'."),
        (1, "What is the Yoruba number 'mẹ́ta'?", "three", ["one", "two", "four"], "ọ̀kan = 1, méjì = 2, mẹ́ta = 3, mẹ́rin = 4."),
        (1, "The Yoruba word for 'water' is", "omi", ["oúnjẹ", "ilé", "oòrùn"], "Omi = water; oúnjẹ = food; ilé = house; oòrùn = sun."),
        (1, "« Ẹ ṣé » means", "Thank you", ["Sorry", "Goodbye", "Welcome"], "Ẹ ṣé (ẹ ṣeun) = thank you."),
    ],
}

# Syllabus topic for each question above, in the same order. The importer matches an existing topic in that
# subject by name (case-insensitive) and creates it if missing.
TOPICS = {
    "English Language": ["Concord", "Concord", "Synonyms", "Antonyms", "Spelling", "Prepositions", "Idioms",
                         "Sentence Structure", "Oral English: Vowels", "Oral English: Stress"],
    "Mathematics": ["Logarithms", "Linear Equations", "Quadratic Equations", "Number Bases", "Statistics",
                    "Commercial Arithmetic", "Coordinate Geometry", "Polygons", "Integration", "Differentiation"],
    "Physics": ["Work, Energy and Power", "Motion", "Work, Energy and Power", "Current Electricity", "Waves",
                "Scalars and Vectors", "Heat Energy", "Lenses", "Radioactivity", "Pressure"],
    "Chemistry": ["Mole Concept", "Periodic Table", "Acids, Bases and Salts", "Non-metals and their Compounds",
                  "Redox Reactions", "Hydrocarbons", "Separation Techniques", "Atomic Structure", "Water",
                  "Mole Concept"],
    "Biology": ["Cell Structure", "Photosynthesis", "Circulatory System", "Digestion", "Genetics", "Nutrition",
                "Diseases and Parasites", "Transport in Plants", "Endocrine System", "Characteristics of Living Things"],
    "Economics": ["Basic Concepts", "Demand", "Elasticity", "Market Structures", "Inflation", "National Income",
                  "Money and Banking", "Factors of Production", "Theory of Production", "Public Finance"],
    "Government": ["Separation of Powers", "The Legislature", "The Legislature", "Rule of Law", "Systems of Government",
                   "Nigerian Constitutional Development", "Nigerian Constitutional Development", "Elections and Franchise",
                   "The Judiciary", "International Organisations"],
    "Literature in English": ["Poetry", "Prose", "Figures of Speech", "Characterisation", "Figures of Speech", "Drama",
                              "Figures of Speech", "Drama", "Poetry", "Prose"],
    "Geography": ["The Earth and the Solar System", "Longitude and Time", "Map Reading", "Rocks", "Climate",
                  "Latitude and Longitude", "Drainage of Nigeria", "The Atmosphere", "Map Reading", "Population"],
    "Commerce": ["Aids to Trade", "Retail Trade", "Insurance", "Transport", "Business Units", "Banking",
                 "Hire Purchase", "Transport", "Trade Discounts", "Introduction to Commerce"],
    "Financial Accounting": ["Accounting Equation", "Double Entry", "Depreciation", "Trial Balance", "Trading Account",
                             "Trading Account", "Final Accounts", "Final Accounts", "Bank Reconciliation", "Petty Cash"],
    "Christian Religious Studies": ["The Exodus", "The Monarchy", "Life of Jesus", "Passion of Jesus", "The Early Church",
                                    "The Prophets", "Christian Living", "The Patriarchs", "The Early Church", "The Prophets"],
    "Islamic Studies": ["Revelation of the Qur'an", "The Qur'an", "Pillars of Islam", "Sawm (Fasting)", "Sirah",
                        "The Caliphate", "Zakat", "The Qur'an", "Sawm (Fasting)", "Salat (Prayer)"],
    "History": ["Colonial Rule", "The Sokoto Caliphate", "Post-Independence Nigeria", "Pre-colonial States",
                "Pre-colonial States", "Nationalism and Independence", "Pre-colonial States", "Post-Independence Nigeria",
                "Pre-colonial States", "Colonial Rule"],
    "Agricultural Science": ["Soil Science", "Crop Production", "Animal Production", "Soil Fertility",
                             "Animal Production", "Crop Production", "Animal Health", "Soil and Water Management",
                             "Animal Production", "Crop Production"],
    "Civic Education": ["Human Rights", "Citizenship", "National Values", "Corruption", "Drug Abuse",
                        "Human Trafficking", "Elections", "Rule of Law", "Human Rights", "Civil Society"],
    "Computer Studies": ["Computer Hardware", "Data Representation", "Computer Hardware", "Computer Memory",
                         "Data Representation", "The Internet", "Computer Software", "Logic Gates", "The Internet",
                         "Computer Security"],
    "Home Economics": ["Nutrition", "Nutrition", "Nutrition", "Nutrition", "Nutrition", "Food Preparation", "Textiles",
                       "Family Living", "Food Preservation", "Nutrition"],
    "Physical and Health Education": ["Ball Games", "Ball Games", "Ball Games", "Olympic Games", "Athletics",
                                      "First Aid", "First Aid", "Communicable Diseases", "Human Anatomy", "Athletics"],
    "Fine Art": ["Colour", "Colour", "Colour", "Colour", "Nigerian Art History", "Nigerian Art History",
                 "Textile Design", "Nigerian Traditional Art", "Drawing", "Nigerian Artists"],
    "Music": ["Rudiments of Music", "Rudiments of Music", "Rudiments of Music", "Musical Terms", "Musical Terms",
              "Scales", "Intervals", "Key Signatures", "African Musical Instruments", "Western Music History"],
    "French": ["Grammar", "Grammar", "Grammar", "Vocabulary", "Grammar", "Grammar", "Vocabulary", "Grammar",
               "Vocabulary", "Vocabulary"],
    "Arabic": ["Vocabulary", "Grammar", "Vocabulary", "Vocabulary", "Vocabulary", "Numbers"],
    "Hausa": ["Greetings", "Numbers", "Vocabulary", "Greetings"],
    "Igbo": ["Greetings", "Numbers", "Greetings", "Vocabulary"],
    "Yoruba": ["Greetings", "Numbers", "Vocabulary", "Greetings"],
}

# Passage-based (stimulus-based) question sets: one passage shared by several questions.
PASSAGES = [
    ("English Language", "Comprehension", "eng-farm-cooperative", "Comprehension passage", (
        "When the rains failed for the second year running, the farmers of Ikeji did not wait for help from "
        "the capital. They pooled their savings and dug a shallow reservoir at the edge of the village, "
        "lining it with clay from the riverbank. The older men doubted that such a small pond could make any "
        "difference, but the young women who organised the work kept careful records of every naira spent and "
        "every bucket of water drawn.\n\n"
        "By the next dry season the reservoir was keeping three hectares of vegetables alive. Traders who had "
        "once driven past Ikeji now stopped to buy tomatoes and peppers. The doubters, it is said, were the "
        "first to ask for a larger reservoir."), [
        (2, "According to the passage, the farmers built the reservoir because", "the rains had failed two years in a row", ["the capital ordered them to", "traders asked for vegetables", "the river had dried up permanently"], "The first sentence says the rains failed for the second year running and they acted without waiting for help."),
        (2, "The young women's records show that they were", "careful and accountable", ["wasteful", "doubtful of the project", "working for the government"], "They 'kept careful records of every naira spent and every bucket of water drawn'."),
        (2, "The word 'pooled', as used in the passage, means", "combined", ["spent", "hid", "borrowed"], "To pool savings is to combine them into one shared fund."),
        (3, "The last sentence suggests that the older men", "changed their minds after seeing the results", ["still opposed the reservoir", "left the village", "built a reservoir of their own"], "Those who doubted it were the first to ask for a larger one: the success convinced them."),
        (2, "Which title best suits the passage?", "Self-Help in Ikeji", ["The Failure of the Rains", "Traders of the Capital", "A Quarrel in Ikeji"], "The passage is about villagers solving their own problem."),
    ]),
    ("Literature in English", "Poetry", "lit-poem-harmattan", "Read the poem and answer the questions", (
        "The harmattan comes like a thief at dawn,\n"
        "stealing the green from the mango leaves;\n"
        "it whispers dust on the window-pane\n"
        "and wraps the town in a grey shawl."), [
        (2, "'The harmattan comes like a thief at dawn' contains", "a simile", ["a metaphor only", "alliteration only", "an oxymoron"], "It compares the harmattan to a thief using 'like'."),
        (2, "'it whispers dust on the window-pane' is an example of", "personification", ["hyperbole", "simile", "onomatopoeia"], "The wind is given a human action: whispering."),
        (2, "The mood of the poem is best described as", "quiet and gloomy", ["joyful and festive", "angry and violent", "humorous"], "Stealing colour, whispering dust and a grey shawl create a quiet, dull mood."),
    ]),
]


def _position(text: str) -> int:
    return int(hashlib.sha256(text.encode()).hexdigest(), 16) % 4


def _row(subject, topic, diff, text, correct, wrongs, expl, passage=None):
    assert len(wrongs) == 3 and correct not in wrongs, text
    opts = list(wrongs)
    pos = _position(text)
    opts.insert(pos, correct)
    letters = "ABCD"
    row = {"subject": subject, "subject_id": SUBJECT_IDS[subject], "topic": topic, "text": text,
           "options": [{"label": letters[i], "text": o} for i, o in enumerate(opts)],
           "explanation": expl, "difficulty": diff, "source": SOURCE, "answer": letters[pos]}
    if passage:
        row["passage"] = passage
    return row


def build():
    assert TOPICS.keys() == Q.keys() and all(len(TOPICS[s]) == len(Q[s]) for s in Q), "TOPICS must match Q"
    rows = [_row(s, t, *q) for s, qs in Q.items() for t, q in zip(TOPICS[s], qs)]
    for subject, topic, key, title, body, qs in PASSAGES:
        p = {"key": key, "title": title, "body": body, "source": SOURCE}
        rows += [_row(subject, topic, *q, passage=p) for q in qs]
    assert len({(r["subject"], r["text"], (r.get("passage") or {}).get("key")) for r in rows}) == len(rows), "duplicate question"
    return rows


if __name__ == "__main__":
    out = Path(__file__).with_name("jamb_starter_questions.json")
    rows = build()
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(f"{len(rows)} questions → {out}")
    print(dict(Counter(r["subject"] for r in rows)))
    print("answer letters:", dict(Counter(r["answer"] for r in rows)))
