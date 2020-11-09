<h1 align="center">Rokoko Studio Live Plugin for Cinema 4D</h1>

[Rokoko Studio](https://www.rokoko.com/en/products/studio) is a powerful and intuitive software for recording, visualizing and exporting motion capture.

This plugin lets you stream your animation data from Rokoko Studio directly into Cinema 4D. It also allows you to easily record and retarget animations.

---

## Requirements
- Cinema 4D **R23** (23.008) or higher
- For live stream data: Rokoko Studio 1.18.0b

## Features
- Live stream data:
    - Multiple actors that can all include both body, face (52 blendshapes) and finger data at the same time
    - Camera data
    - Props data
- Remote control Rokoko Studio from within Cinema 4D
- Easily retarget motion capture animations

## Installation
1. Download the Rokoko Studio Live plugin for Cinema 4D here: TODO
2. Just like with any other Cinema 4D plugin the downloaded archive needs to be unzipped into Cinema 4D's plugins folder.
3. Start Cinema 4D (or restart it, if it was already running).

#### Note on step 2:
In Cinema 4D there are multiple possible locations for the plugins folder, and you can even define custom locations in Preferences. Nowadays, the recommended folder is in Cinema 4D's folder inside an user's home directory. If you have difficulties locating it, there's an easy way to find it from witthin Cinema 4D:
- Open the Preferences
- At the bottom there's a button "Open Preferences Folder..."
- In the opened directory, you should see a folder "plugins". That's it.

---

## For the Impatient: Making the Puppets Dance With Only Four Clicks
These steps assume you are already familiar with Rokoko Studio, have enabled Live Streaming to Cinema 4D and in Rokoko Studio loaded a scene and started playback. Just so there's some motion data to be received and displayed in Cinema 4D. If you don't know how to achieve this, please skip to the next section.

1. Open the Rokoko Studio Live Manager from the menu *Extensions* choose *Rokoko Studio Live*.
  <img src="https://user-images.githubusercontent.com/73877880/98574796-a905f980-22b8-11eb-9e32-6219ea0a64db.png" width="40%"/>

2. On the *Connection* tab, click the "Connect" button (this step can be skipped later on using the auto-connect feature, see below). Depending on the scene playing currently in Rokoko Studio you should see names of your actors and props being displayed.
  <img src="https://user-images.githubusercontent.com/73877880/98575236-36494e00-22b9-11eb-8778-087e81d28199.png" width="30%"/> &nbsp;&nbsp;&nbsp;
  <img src="https://user-images.githubusercontent.com/73877880/98575260-3f3a1f80-22b9-11eb-8f00-2ffe2d5392b5.png" width="30%"/>

3. On the *Tags* tab, click the "+" button and choose "Create Connected Studio Scene"
  <img src="https://user-images.githubusercontent.com/73877880/98576843-698cdc80-22bb-11eb-8cfe-e4e2b69891a1.png" width="40%"/>
  This will automatically create Rokoko Newton characters for actors and Null objects for props as needed for the Live stream received from Rokoko Studio.
  <img src="https://user-images.githubusercontent.com/73877880/98577107-c38da200-22bb-11eb-836c-13b5925d2eb2.png"/>

4. On the *Player* tab click "Start Player". Done.
  <img src="https://user-images.githubusercontent.com/73877880/98577256-f768c780-22bb-11eb-8f5e-336aff21c74d.png"/>

Now, that maybe your immediate appetite for results is satisfied, lets take a look at what we just did exactly and what other options you have when working with Rokoko Studio Live.


## Introduction

### Plugin Components
The Rokoko Studio Live plugin consists of two main components.
1. *Rokoko Studio Live Manager*
  The Rokoko Studio Live Manager is basically your central point to control almost everything Rokoko Studio Live related, that's going on in your scene.
  <img src="https://user-images.githubusercontent.com/73877880/98577899-e40a2c00-22bc-11eb-9eef-aa2dd112c751.png" width="40%"/>

2. *Rokoko Tag*
  The Rokoko Tag can be assigned to arbitrary objects and it will, depending on the type of object its assigned to, take the role of either an actor, an actor's face or a prop. It will basically be the connection between Rokoko Studio's motion data and the actual objects in Cinema 4D's scene.
  <img src="https://user-images.githubusercontent.com/73877880/98578165-4531ff80-22bd-11eb-91e7-211933c968cf.png"/>
  <img src="https://user-images.githubusercontent.com/73877880/98577975-fedca080-22bc-11eb-8bed-93be1ee18231.png"/>

### A few Terms, we Should Agree on
- "Studio" will be used synonymously with "Rokoko Studio", it does _not_ refer to the Studio Version of Cinema 4D, which was available for previous versions of Cinema 4D.
- "Rokoko Manager" or "Manager": These will be short forms, when talking about the Rokoko Studio Live Manager dialog.
- "Tag": If not further specified, the term Tag will always refer to the Rokoko Tag.
- "Stream" or "Live Data": Hereby the data transmitted by Studio is referenced, regardless of being actual live data (from a SmartSuit for example) or a previously recorded scene, that's played back by Rokoko Studio.
- "Clip": Basically a reference to a file storing a Stream previously received from Rokoko Studio.

### Overview of Rokoko Studio Live Manager
The Manager has six tabs dedicated to certain tasks or purposes.
- Connection
  - Connect to or disconnect from Rokoko Studio
  - Edit connection settings
- Global Clips and Project Clips
  - Basically libraries of previously recorded motion data clips. More on this later.
- Tags
  - Probably the most important tab (together with the Player)
  - Lists all Rokoko Tags contained in the current scene together with the object they are assigned to, as well as means to select the data used by a tag.
  - Here one can also quickly add premade Rokoko Newton characters to a scene or even replicate an entire scene currently received from Studio in a single click.
- Player
  - Here you can start/stop playback of motion data
  - Review incoming data
  - Record and bake incoming motion data
- Command API
  - Provides means to remote control certain tasks in Rokoko Studio.

### Overview of Rokoko Tag
When being assigned to an object, the Rokoko Tag will try to automatically detect its type. One can still change the type later, though it can only be changed to types suitable for the object it is assigned to.

When the tag is assigned to...
- a Joint or an arbitrary object with a Joint as _first_ child, the tag will assume to be of type Actor.
- an Object which carries a PoseMorph tag, the tag will assume to be of type Face.
- any other object, it will assume to be of type Prop.

Note: As also joints or objects with PoseMorph tags could be used as Props, you can always change the type of the tag to Prop.

Depending on its type the Rokoko Tag offers a bunch of options grouped into four tabs.
- Tag Properties: The main group, where you can select the data assigned to this tag.
- Control: Here are means to play the assigned data, have a character return tto T-Pose or bake motion data into keyframes.
- Mapping: This tab is only available for tags of type Actor or Face. It offers means to auto-detect, map/retarget and manually change joints and face poses, to store and fine tune the T-Pose and also manage (store and apply) presets of thew mapping tables.
- Info: Displays some meta data of an actor, face or prop (for example its name and color). A possible use-case could be to setup an Xpresso tag to automatically have a label with the name of an actor.


## Establishing a Connection
In order to receive motion data from Studio, both sides (Studio and C4D) need to be configured correctly. No worries, both sides are actually properly configured by default. A change of the defaults is only needed, if for example the preconfigured port (14043) is already in use for something different on your system.

### Enabling Rokoko Studio Live in Rokoko Studio
- In Rokoko Studio go to settings and click on **Studio Live** in the dropdown menu and enable the Cinema 4D data stream. You can customize the streaming address and port by clicking the cogwheel icon at the top left.

  <img src="https://user-images.githubusercontent.com/73877880/98578673-f042b900-22bd-11eb-9d9b-1fce247d667d.png" height="500" /> &nbsp;&nbsp;&nbsp;
  <img src="https://user-images.githubusercontent.com/73877880/98578703-f9cc2100-22bd-11eb-879e-db48a64b0e3d.png"/>

### Receiving the Data in Cinema 4D
- Open the Rokoko Studio Live Manager from the *Extensions* menu. There are six tabs of which the leftmost one is the "Connection" tab. It should be open by default. As long as the default port (14043) is fine for you and you didn't change it in Studio, all you need to do is press the "Connect" button.

  <img src="https://user-images.githubusercontent.com/73877880/98574796-a905f980-22b8-11eb-9e32-6219ea0a64db.png"/> &nbsp;&nbsp;&nbsp;
  <img src="https://user-images.githubusercontent.com/73877880/98575236-36494e00-22b9-11eb-8778-087e81d28199.png"/> &nbsp;&nbsp;&nbsp;
  <img src="https://user-images.githubusercontent.com/73877880/98575260-3f3a1f80-22b9-11eb-8f00-2ffe2d5392b5.png"/>

#### Connection Status
The status of the connection is displayed as a coloured dot nect to the connect button as well as in the upper right corner of the Manager.
There are four different states:

- Red: Rokoko Studio Live is _not_ connected
  <img src="https://user-images.githubusercontent.com/73877880/98579057-66dfb680-22be-11eb-9525-f4f2aca6f8ba.png"/>

- Green: Rokoko Studio Live is connected and the stream was properly detected
  <img src="https://user-images.githubusercontent.com/73877880/98579106-73fca580-22be-11eb-9a33-667c39b57f81.png"/>

- Orange: Rokoko Studio Live has opened a connection, but has not been able to detect a stream. This may have a bunch of reasons:
  - Rokoko Studio is not running
  - Rokoko Studio is running, but Rokoko Studio Live has not been enabled
  - Rokoko Studio is running and has Rokoko Studio Live enabled, but it is using a different port number, than is used inside Cinema 4D.
  <img src="https://user-images.githubusercontent.com/73877880/98579245-a1e1ea00-22be-11eb-8279-64d6550287ca.png"/>

- Grey: There is no connection to Rokoko Studio, but clips are being played inside Cinema 4D. More on this later.
  <img src="https://user-images.githubusercontent.com/73877880/98579288-b32af680-22be-11eb-8fae-6e7df9bb60c7.png"/>

#### Changing the Port Number
In order to edit the connection settings, Rokoko Studio Live needs to be disconnected (red dot). Clicking the "..." button left of the connection offers an "Edit..." option.
  <img src="https://user-images.githubusercontent.com/73877880/98579501-07ce7180-22bf-11eb-8c7d-5be9da634cf9.png"/> &nbsp;&nbsp;&nbsp;
  <img src="https://user-images.githubusercontent.com/73877880/98579449-f8e7bf00-22be-11eb-9395-940d7c55e705.png"/>

#### Auto Connect
The checkbox left of the "Connect" button enables the Auto Connect feature. If set, Cinema 4D will automatically open this connection when starting up. No worries, it's not doing much and should hurt any other work you are doing in Cinema 4D.


## Preparing a Custom Character for Streaming
While Rokoko Studio Live for Cinema 4D comes with a set of Rokoko Newton characters, it can of course be used with arbitrary characters.

### Make sure a custom character model is ready for Studio Live
The character in Cinema 4D has to be in T-pose and should be placed at the origin:

  <img src="TODO" height="450"/>

Also it is advised, though not absolutely necessary, to have the hip joint parented by another object. While this may be an arbitrary object, either a Null object or another joint object is recommended.

**For SmartGloves:** Make sure that the character's hands and fingers are posed as close as possible to the following pose to get the best
possible retargeting of finger animation. All fingers should be straight and the thumb should be rotated 45 degrees away from the other fingers.

  <img src="TODO"/>

## Streaming Motion Data

### General Workflow
1. Assign a Rokoko Tag to the character rig or object (for props) to be driven by Rokoko Studio Live (one can also simply create premade Rokoko Newton characters from the "Tags" tab in Rokoko Manager).
2. For characters or faces properly prepare the rig (establish a mapping of joints or face poses and store the T-Pose)
3. Select the data to be used by this tag.
4. Start the Player to review everything is working as expected.
5. Start a new recording.
6. When done with the recording, decide what to do with the received data. Save it as a clip for later use or directly bake it into keyframes.

### Streaming Motion Data

- After establishing a connection to Studio as described above, go to the "Tags" tab in Rokoko Manager.
- If not already done so, either...
  - prepare your custom rig by assigning a Rokoko Tag to its root object (more details on this below)
  - or press the "+" buttton in the top-left of the Tags tab to insert a default characters into your scene.
- On the "Tags" tab you should now find all Rokoko Tags listed.
- Fill all joint fields by pressing “Auto Detect Rig” and check if all joints are correctly filled in. One can correct falsely detected or missing joints simply by dragging the respecttive Joint from Object Manager into table.
- Ensure that the selected character is in T-Pose and then press “Set as T-Pose”

  <img src="TODO"/>

- Done! Your character now should be animated by the live data:

  <img src="TODO" height="500"/>


### Streaming Face and Prop Data
- This uses the exact same workflow as streaming character data
- Just apply a Rokoko Tag to the face mesh (the object that carries the PoseMorph tag) for face data or a prop object for prop data and then follow the steps above
- Done! Your face mesh or prop should now be animated by the live data

  <img src="TODO" height="400"/> &nbsp;&nbsp;&nbsp;
  <img src="TODO" height="400"/>

---

## Recording and Baking


---

## Rokoko Studio Live Manager in Detail

---

## Rokoko Tag in Detail

---

## Retargeting
Instead of directly driving a custom character with a Rokoko Tag as described above, one can also retarget motion using the new Character Definition and Solver tags new in Cinema 4D R23.

- Simply create a Newton character (or an entire Studio scene) via the "+" button in the upper left of the Tags tab in Rokoko Manager. You will find, that these characters already come with a preconfigured Character Definition tag.

  <img src="TODO"/>

- Now set up your a custom character and create a Character Definition tag as described in [Cinema 4D's documentation](https://help.maxon.net/r23/en-us/#html/TCHARACTERDEF.html).

  <img src="TODO"/>

- Finally also create a [Character Solver tag](https://help.maxon.net/r23/en-us/#html/TCHARACTERSOLVER.html%3FTocPath%3DCharacter%2520Menu%7CMotion%2520Retargeting%7CMotion%2520Solver%2520Tag%7C_____0) and drag in the two Character Definition tags (the one from Newton as Source and tthe one just created as Target)

  <img src="TODO"/>

- Done!

   [<img src="TODO" width="50%">](https://youtu.be/Od8Ecr70A4Q)

---

## Changelog

#### 1.0.TODO
- First version of Rokoko Studio Live for Cinema 4D
- Supported motion data: SmartsuitPro, SmartGloves, Face and Props
- Character animation and recording
- Face animation and recording
- Studio Command API support
