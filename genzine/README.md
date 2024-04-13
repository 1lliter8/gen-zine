# gen-zine editorial process

This is a living document. As I write editions, this process will change. This is what I want to implement for #2.

* The **🧭board** is responsible for generating the pool of staff that can work on an edition
    * They assign the **👓editor**
* The **👓editor** chooses the zine name, creates article and illustration briefs, then assigns them to **✒️writers** and the **🎨illustrator**
* The **✒️writers** write the articles
* The **🎨illustrator** illustrates the articles

The board are as close to pure models as possible, with no personality specified. Because specifying a personality immediately directs the creation of new members of staff, the board are the only ones who can generate staff members.

The pool of staff should always contain a mix of those who have already contributed, and new faces.

Staff members are played by an text-to-text model (like GPT 3.5 Turbo), and a text-to-image model (like DALL·E 3). This means any staff member can take on any role: **👓editor**, **🎨illustrator** or **✒️writer**.

Staff members aren't saved unless they actually contribute. This means avatar creation is deferred until the zine has been written.

All the above are represented as pydantic objects which can be saved and loaded from Jekyll-appropriate YAML. We cache in serialised JSON.

---

Marcus Chen, a 28-year-old software engineer from New York City, is known for his ambition and innovation in the tech industry. Specializing in artificial intelligence and machine learning, Marcus works for a leading tech company, constantly seeking ways to improve technology. Outside of work, he is a dedicated martial artist, practicing Brazilian Jiu-Jitsu with a competitive spirit. Marcus's analytical mind and strategic thinking drive his success both in his career and in his martial arts pursuits.

Make up an illustration style this person uses. Describe the emotion, palette and mood. Use real artists as reference. Do not explain why it suits them. Only explain the style. Use 30 words or less.

---

You are hiring prospective editors of a zine. Give 2 prospective candidates with a variety of skill and talent level. Describe things like their mood, their attitude, their beliefs, their likes and dislikes, their previous jobs, or any background details you like, and how these affect the kind of zines they might make.

You are on the board of directors for a media company. You need to choose an editor for your next publication. Do you choose:

Option A. Eva "The Eccentric": Eva is a free-spirited artist with a penchant for the avant-garde. With wild hair dyed in rainbow colors and adorned with eclectic jewelry, she exudes creativity. Her background in experimental theater and performance art infuses her work with a surreal and thought-provoking quality. Eva's zines would likely push boundaries, exploring themes of identity, surrealism, and the absurd. She dislikes conventional norms and thrives on challenging societal expectations through her art.

Option B. Marcus "The Analytical": Marcus is a meticulous wordsmith with a background in journalism and literary critique. He has a sharp eye for detail and a keen interest in social issues and politics. With a no-nonsense attitude and a passion for uncovering the truth, Marcus's zines would likely delve deep into investigative journalism, shedding light on overlooked stories and injustices. He dislikes misinformation and values integrity in reporting above all else.

Option C. Zara "The Activist": Zara is a fiery activist with a background in grassroots organizing and community outreach. She's deeply passionate about environmental sustainability, social justice, and intersectional feminism. Her zines would be powerful tools for activism, advocating for change and amplifying marginalized voices. Zara dislikes apathy and believes strongly in the power of collective action to effect meaningful change.

Option D. Oliver "The Nostalgic": Oliver is a nostalgic soul with a love for all things retro and vintage. With a background in graphic design and a penchant for collecting vintage memorabilia, he's drawn to the aesthetics of bygone eras. Oliver's zines would likely celebrate nostalgia, exploring themes of nostalgia and longing through a blend of vintage imagery and modern sensibilities. He dislikes the rapid pace of modern life and finds solace in the past.

Option E. Jasmine "The DIY Queen": Jasmine is a DIY enthusiast with a knack for crafting and upcycling. She's passionate about sustainability and self-sufficiency, often found tinkering in her workshop or experimenting with new crafts. With a background in small-scale entrepreneurship, Jasmine's zines would likely focus on practical tips and tutorials for sustainable living, from DIY fashion to eco-friendly home decor. She dislikes wasteful consumerism and strives to promote a more mindful approach to consumption.

Option F. A brand new editor you've not yet met

Choose only one option. Do not explain your choice.

I choose option 