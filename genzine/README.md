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
