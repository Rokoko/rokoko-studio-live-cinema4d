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

### A few Terms we Should Agree on as These are Frequently Used Throughout These Docs
- "Studio" will be used synonymously with "Rokoko Studio", it does _not_ refer to the Studio Version of Cinema 4D, which was available for previous versions of Cinema 4D.
- "Rokoko Manager" or "Manager": These will be short forms, when talking about the Rokoko Studio Live Manager dialog.
- "Tag": If not further specified, the term Tag will always refer to the Rokoko Tag.
- "Stream" or "Live Data": Hereby the data transmitted by Studio is referenced, regardless of being actual live data (from a SmartSuit for example) or a previously recorded scene, that's played back by Rokoko Studio.
- "Clip": Basically a reference to a file storing a Stream previously received from Rokoko Studio.

---

## For the Impatient: Making the Puppets Dance With Only Four Clicks
These steps assume you are already familiar with Rokoko Studio, have enabled Live Streaming to Cinema 4D and in Rokoko Studio loaded a scene and started playback. Just so there's some motion data to be received and displayed in Cinema 4D. If you don't know how to achieve this, please skip to the next section.

1. Open the Rokoko Studio Live Manager from the menu _Extensions_ choose _Rokoko Studio Live_.

   <img src="https://user-images.githubusercontent.com/73877880/98574796-a905f980-22b8-11eb-9e32-6219ea0a64db.png" width="20%"/>

2. On the *Connection* tab, click the "Connect" button (this step can be skipped later on using the auto-connect feature, see below). Depending on the scene playing currently in Rokoko Studio you should see names of your actors and props being displayed.

  <img src="https://user-images.githubusercontent.com/73877880/98575236-36494e00-22b9-11eb-8778-087e81d28199.png" width="40%"/> &nbsp;&nbsp;&nbsp; <img src="https://user-images.githubusercontent.com/73877880/98575260-3f3a1f80-22b9-11eb-8f00-2ffe2d5392b5.png" width="40%"/>

3. On the *Tags* tab, click the "+" button and choose "Create Connected Studio Scene"

  <img src="https://user-images.githubusercontent.com/73877880/98576843-698cdc80-22bb-11eb-8cfe-e4e2b69891a1.png" width="40%"/>

  This will automatically create Rokoko Newton characters for actors and Null objects for props as needed for the Live stream received from Rokoko Studio.

  <img src="https://user-images.githubusercontent.com/73877880/98577107-c38da200-22bb-11eb-836c-13b5925d2eb2.png"/>

4. On the *Player* tab click "Start Player". Done.

  <img src="https://user-images.githubusercontent.com/73877880/98577256-f768c780-22bb-11eb-8f5e-336aff21c74d.png"/>

5. For now press "Stop Player".

Hopefully your immediate appetite for results is satisfied, lets take a look at what we just did exactly and what other options you have when working with Rokoko Studio Live.

---

## Introduction

### Plugin Components
The Rokoko Studio Live plugin consists of two main components: **Rokoko Studio Live Manager** and **Rokoko Tag**.

#### Overview of Rokoko Studio Live Manager

<img src="https://user-images.githubusercontent.com/73877880/98577899-e40a2c00-22bc-11eb-9eef-aa2dd112c751.png" width="40%"/>

The Rokoko Studio Live Manager is basically your central point to control almost everything Rokoko Studio Live related, that's going on in your scene.

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

#### Overview of Rokoko Tag
The Rokoko Tag can be assigned to arbitrary objects and it will, depending on the type of object its assigned to, take the role of either an actor, an actor's face or a prop. It will basically be the connection between Rokoko Studio's motion data and the actual objects in Cinema 4D's scene.

<img src="https://user-images.githubusercontent.com/73877880/98578165-4531ff80-22bd-11eb-91e7-211933c968cf.png"/> &nbsp;&nbsp;&nbsp;
<img src="https://user-images.githubusercontent.com/73877880/98577975-fedca080-22bc-11eb-8bed-93be1ee18231.png"/>

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

---

## Establishing a Connection
In order to receive motion data from Studio, both sides (Studio and C4D) need to be configured correctly. No worries, both sides are actually properly configured by default. A change of the defaults is only needed, if for example the preconfigured port (14043) is already in use for something different on your system.

### Enabling Rokoko Studio Live in Rokoko Studio
- In Rokoko Studio go to settings and click on **Studio Live** in the dropdown menu and enable the Cinema 4D data stream. You can customize the streaming address and port by clicking the cogwheel icon at the top left.

  <img src="https://user-images.githubusercontent.com/73877880/98578673-f042b900-22bd-11eb-9d9b-1fce247d667d.png" height="500" /> &nbsp;&nbsp;&nbsp;
  <img src="https://user-images.githubusercontent.com/73877880/98578703-f9cc2100-22bd-11eb-879e-db48a64b0e3d.png"/>

### Receiving the Data in Cinema 4D
- Open the Rokoko Studio Live Manager from the *Extensions* menu. There are six tabs of which the leftmost one is the "Connection" tab. It should be open by default. As long as the default port (14043) is fine for you and you didn't change it in Studio, all you need to do is press the "Connect" button.

  <img src="https://user-images.githubusercontent.com/73877880/98574796-a905f980-22b8-11eb-9e32-6219ea0a64db.png" width="20%"/>

  <img src="https://user-images.githubusercontent.com/73877880/98575236-36494e00-22b9-11eb-8778-087e81d28199.png" width="40%"/> &nbsp;&nbsp;&nbsp;
  <img src="https://user-images.githubusercontent.com/73877880/98575260-3f3a1f80-22b9-11eb-8f00-2ffe2d5392b5.png" width="40%"/>

#### Changing the Port Number
In order to edit the connection settings, Rokoko Studio Live needs to be disconnected (red dot). Clicking the "..." button left of the connection offers an "Edit..." option.

  <img src="https://user-images.githubusercontent.com/73877880/98579501-07ce7180-22bf-11eb-8c7d-5be9da634cf9.png"/> &nbsp;&nbsp;&nbsp;
  <img src="https://user-images.githubusercontent.com/73877880/98579449-f8e7bf00-22be-11eb-9395-940d7c55e705.png"/>

---

## Streaming Motion Data

### General Workflow
1. Establishing a connection to Studio as described above.
2. Assign a Rokoko Tag to a character rig or object (for props) to be driven by Rokoko Studio Live. Or simply create a premade Rokoko Newton character from the "Tags" tab in Rokoko Manager (these already have a Rokoko Tag assigned).
3. For characters or faces properly prepare the rig (establish a mapping of joints or face poses and store the T-Pose), see below
4. Select the data to be used by this tag.
5. Start the Player to review everything is working as expected.
6. Start a new recording.
7. When done with the recording, decide what to do with the received data. Save it as a clip for later use or directly bake it into keyframes.

### Preparing a Character Rig for Rokoko Studio Live
While Rokoko Studio Live for Cinema 4D comes with a set of Rokoko Newton characters, it can of course be used with arbitrary characters.

Assume there's an arbitrary character in a scene, one wants to use with Rokoko Studio Live:

1. Make sure the character is in T-Pose. Also it should be placed in world's origin.

  <img src="https://user-images.githubusercontent.com/73877880/98582390-33535b00-22c3-11eb-9f5a-23b0e88539fd.png" height="450"/>

  **Note:** Also it is advised, though not absolutely necessary, to have the hip joint parented by another object. While this may be an arbitrary object, either a Null object or another joint object is recommended.

  **For SmartGloves:** Make sure that the character's hands and fingers are posed as close as possible to the following pose to get the best possible retargeting of finger animation. All fingers should be straight and the thumb should be rotated 45 degrees away from the other fingers.

  <img src="https://user-images.githubusercontent.com/73877880/98582615-80373180-22c3-11eb-963a-09c8f0d77c73.png" width="40%"/> &nbsp;&nbsp;&nbsp;
  <img src="https://user-images.githubusercontent.com/73877880/98582667-90e7a780-22c3-11eb-877f-10e7374c405e.png" width="40%"/>

2. Assign a Rokoko Tag to the root object the character.

  **Note:** If a character has no explicit root object, but the hip joint serves as a root, one can assign the tag to the hip object. This is not recommended, though, as one will loose certain degrees of freedom. For example the character can no longer be freely positioned and rotated in space, but it will always act upright around world's origin.

3. Select the new tag, to see its parameters in the Attribute Manager and take a look at the "Mapping" tab.
4. Click the “Auto Detect Rig” button. Actually this has happened implicitly already, when the tag was assigned (so in this example this click is kind of redundant), but lets assumed you did changes to the rig, after assignment of the tag, then the rig should be re-detected.
5. Now, check the results of the rig detection in the tables below and fix any issues, that may have occurred.

  Possible issues to look out for:
  - Undetected body parts, the joint link is empty
  - Missdetected body parts, a wrong joint got assigned to a certain body part

  Such issues can be easily corrected, simply by dragging the correct joints from the Object Manager into their respective slots in the Mapping table.

6. After all joints have been correctly assigned, press "Set as T-Pose". Again, if the tag gets created on a character which is already in T-Pose, this click is not needed, as it happens implictly, when the tag gets assigned.
7. Finally choose the motion data to be used for this character (either in the tag's "Properties" tab in Attribute Manager or using the "Tags" tab in Rokoko Manager).
8. Done! You are now ready to play motion data with this character, which can then be saved ito clips or baked into keyframes.

  <img src="https://user-images.githubusercontent.com/73877880/98613012-ba212b80-22f5-11eb-84f1-12992260f73d.gif"/>


### Preparing a Face or Prop for Rokoko Studio Live
- This is basically the same workflow as preparing a character rig for Rokoko Studio Live (described above)
- For Faces: Apply a Rokoko Tag to the face mesh (the object that carries the PoseMorph tag) and then follow above workflow.
  - Differences in workflow:
    - Obviously a face needs no T-Pose
    - Step 4: The button is labeled "Auto Detect Poses"
    - Step 5: Unfotunately Poses can not be dragged from a PoseMorph tag into the Mapping table. Instead one has to enter the Pose names manually.
    - Step 6 doesn't apply
- For Props: Apply a Rokoko Tag to a prop object
  - Differences in workflow:
    - Props have no T-Pose nor any mapping tables
    - Therefore the process boils down to assigning the tag and choosing data in step 7.
- Done!

  <img src="https://user-images.githubusercontent.com/73877880/98613477-ae823480-22f6-11eb-97d9-bc4fff4bd807.gif" height="400"/>

---

## Recording and Baking
So far this documentation talked a lot about setting up a connection and preparing character rigs, etc. and when following the introductory steps, you may have started the player and saw some character moving in the viewport. But of course one not only wants to see a character moving in the viewport, one also wants to record and use the motion data in the scene.

### General Workflow
1. A connection has been set up as described above and Studio is streaming motion data.
2. At least one character (or face or prop for that matter) has been set up as described above.
3. Open the Rokoko Manager and activate the Player tab.
4. Press "Start Player" (more on the various options of the player below).
5. When the actors are ready, press "Start Recording".
6. As soon as the actors are done with their performance press "Save Recording..."
7. A new dialog opens, which provides means to cut the recorded motion data, store it as a clip for later use or directly bake it into keyframes.
8. By closing this dialog, the buffer with the recorded motion data gets flushed.

### Live Data and Clips
In order to fully understand all options in the Save Recording dialog, we need to quickly explain Clips. So far all examples above more or less implicitly assumed Studio streaming motion data to Cinema 4D, which is then used to animate a character. But this is only part of the truth, because actually one can always decide to not just play the motion data and bake it into keyframes, but also to save the motion data to a file. This is called a Clip. Clips can be stored anywhere on disc. Inside Cinema 4D the reference to such Clips can be stored either globally (Global Clips, meaning one can use these in every project in Cinema 4D) or just the current document/project (Project Clips). This is also the reason for the two tabs "Global Clips" and "Project Clips" in Rokoko Manager, that were skipped so far in this documentation and will be described a bit further down below. The point is, when settting up a scene and assigning data to tthe Rokoko Tags, one can not only choose live data, but also from all Clips available in a project (so all Global Clips plus the Project Clips). One can freely mix these. One character may be driven by actual live data from Studio, while two others have clips assigned.

A possible use case could be to set up a scene with more characters than one has Smartsuits available. In a first take one would only record live data and save this into a Clip. Now, you assign this recorded Clip to the fist set of characters and set a second set of characters to use live data. Now, when recording you can actually see the first set of characters performing the motion of the first take, while the second set of characters reflects the live performance.


### The Save Recording Dialog
<img src="https://user-images.githubusercontent.com/73877880/98611011-50068780-22f1-11eb-88aa-d7c522cd7597.png" height="400"/>

- With the two sliders on top ('First Frame" and 'Last Frame') one can interactively tweak the beginning and the end of the recording. Baking and saving only happens in the range from first to last frame specified here.
- The "Bake Keyframes" section offers a bunch of parameters to influence the process of keyframe creation.
  - "Timing": Options are "Studio Time" and "By Frame".
    - "Studio Time" means the keyframes will be positioned in time based on the timing information contained in Studio's data stream. It's also taking into acount the frame rate configured for the project in Cinema 4D. This will result in the same timing as in Studio. E.g. if two frames are a second apart in Studio, they will also be a second apart in Cinema 4D.
    - "By Frame" actually ignores the timing completely. Keyframes will be created on a per frame basis. The keyframes for each frame in the motion data will be created on consecutive frames in the Cinema 4D project.
  - "Skip Frames": Here one has various (frankly speaking quite simple) options to reduce the amount of keyframes being created. Either by directly skipping every n'th frame of the motion data or by specifying FPS (which actually is more a KPS, keyframes per second).
  - "Length": This option decides, what happens if the motion data is longer than the currently set project length inside of Cinema 4D.
    - "Extend Project's End Time": The maximum time of the project inside Cinema 4D will be increased to the last baked keyframe.
    - "Stop at Project's End Time": The baking will stop, when the end of Cinema 4D's project is reached.
    - "Ignore": All keyframes will be baked ignoring the end of the project in Cinema 4D. This may result in keyframes located after the end of the project. In Cinema 4D this imposes no issues, one can manually adjust the project end time later manually.
  - "Create New Take": When checked, a new Take will be created and the keyframes will be baked into this new Take. Otherwise the keyframes will be created in the current Take (which may also be the ever existing Main Take, if one is not interested in Takes at all.
  - "Activate New Take": When checked and baking is finished, the new Take will be made the active/current Take.
  - "Wipe Existing Animation": When checked, any keyframes existing in the Take to be baked into will be deleted prior to baking. Of course this only applies to objects and curves (position and rotation) being in control of the plugin. As keyframes can also be inherited from other Takes, this option also applies, when a new Take gets created. In tthis case it means, any keyframes the new Take inherited from the Main Take would be wiped prior to baking.
  - "Advance Current Frame": If checked, the current frame of the project will be set after the last baked keyframe. This may be useful to for example "stamp" a motion clip multiple times into a project.
  - "Include File Clips": If set, the baking will not only create keyframes for the just recorded live data, but also for all other characters that have been involved and were fed by data from Clips.
  - Button "Bake Keyframes at 0": Pressing this button will start the actual baking process, beginning at Cinema 4D's frame zero.
  - Button "Bake Keyframes at Current": Same as "Baking Keyframes at 0", but the first keyframe will be created at the current frame. Useful in conjuction with "Advance Current Frame" to consecutively bake a recording multiple times.
- The "Save Clip to File" section offers a bunch of parameters to influence the process of keyframe creation.
  - Choose a "Name" and a filepath ("Path") for the Clip.
  - Button "Store Global Clip": Saves the motion data to the file specified and afterwards creates a reference to this Clip in the Global Clips library.
  - Button "Store Project Clip": Saves the motion data to the file specified and afterwards creates a reference to this Clip in the Project Clips library. The file may still be saved outside the project directory, the differentiation global/project is all about the reference and where this clip is available afterwards (either in all Cinema 4D projects or only the current project).
  - "Use New Clip": If set, all involved tags that referred to live data will be switched to use the new Clip instead.

---

## Rokoko Studio Live Manager in Detail

### Connection
This tab is all about the connection to Rokoko Studio.

The "Connect/Disconnect" button (label changes according to connection state) allows to either connect to or disconnect from Studio.

#### Connection Status
The status of the connection is displayed as a coloured dot left of the Connect button as well as in the upper right corner of the Manager.
There are four different states:

- Red: Rokoko Studio Live is _not_ connected

  <img src="https://user-images.githubusercontent.com/73877880/98579057-66dfb680-22be-11eb-9525-f4f2aca6f8ba.png"/>

- Green: Rokoko Studio Live is connected and the stream was properly detected

  <img src="https://user-images.githubusercontent.com/73877880/98579106-73fca580-22be-11eb-9a33-667c39b57f81.png"/>

  In this state additional information like the names of actors and props, the data available for an actor (Smartsuit Pro, Smartgloves, Face) as well as the frames per second (FPS) is displayed on the Connection tab.

- Orange: Rokoko Studio Live has opened a connection, but has not been able to detect a stream. This may have a bunch of reasons:
  - Rokoko Studio is not running
  - Rokoko Studio is running, but Rokoko Studio Live has not been enabled
  - Rokoko Studio is running and has Rokoko Studio Live enabled, but it is using a different port number, than is used inside Cinema 4D.

  <img src="https://user-images.githubusercontent.com/73877880/98579245-a1e1ea00-22be-11eb-8279-64d6550287ca.png"/>

- Grey: There is no connection to Rokoko Studio, but clips are being played inside Cinema 4D.

  <img src="https://user-images.githubusercontent.com/73877880/98579288-b32af680-22be-11eb-8fae-6e7df9bb60c7.png"/>

  *What is this?*
  Normally the Player will use a given live connection as a kind of clock. The update of the characters in viewport basically happens when being triggered by a new frame being received from the live connection. This happens regardless of the data from the live stream actually being used by any tag. But if there is no connection to Rokoko Studio, then there is no stream, then there are no frames received. In this case the player needs to be its own clock and this is indicated by the grey connection status. In order to switch to this mode, there must not be a connection. This means, if Cinema 4D is connected to Rokoko Studio, but Studio is not transmitting any data (state orange above), a requester will open, asking to disconnect before starting the player. One can still decide to keep the connection, but then playback will not start until Studio actually starts transmitting data (and thus the status changed to green).


#### Auto Connect
The checkbox left of the "Connect" button enables the Auto Connect feature. If set, Cinema 4D will automatically open this connection when starting up. No worries, it's not doing much and should _not_ hurt any other work you are doing in Cinema 4D.

#### Changing Connection Parameters

In order to edit the connection settings, Rokoko Studio Live needs to be disconnected (red dot).
Clicking the "..." button left of the connection pops up a menu, which offers an "Edit..." option.

  <img src="https://user-images.githubusercontent.com/73877880/98579501-07ce7180-22bf-11eb-8c7d-5be9da634cf9.png"/> &nbsp;&nbsp;&nbsp;
  <img src="https://user-images.githubusercontent.com/73877880/98579449-f8e7bf00-22be-11eb-9395-940d7c55e705.png"/>

In the "Edit Connection" dialog is divided into two sections "Live Connection" and "Command API Connection".
- "Live Connection":
  - "Name": The connection has an arbitrary name and one can change it in case one dislikes the term "Studio Connection"...
  - "Port": This is the port Rokoko Studio Live plugin will listen on in order to receive motion data from Rokoko Studio.
- "Command API Connection": These parameters are used to remote control Rokoko Studio.
  - "IP": The IP address.
  - "Port": The Command API port set in Rokoko Studio.
  - "Key": The Command API key, that is displayed in Studio for the Command API connection.

#### Create Scene
When connected, clicking the "..." button left of the connection pops up a menu, which offers this "Create Scene" option. This is identical to the "Create Studio Scene" option in the popup menu on the Tags tab. It will insert Rokoko Newton chracters and Null objects (for props) needed for the currently streamed motion data from Studio. All tags already configured, so you can press "Start Player" immediately after.


### Global Clips
This is a simple library to reference motion data stored in Clips. The Clips Referenced in this Global Clips library are available Cinema 4D wide.

#### The + Button
The "+" button presents a menu providing the following options:
- "Add File...": Choose a previously saved motion data file from disc and its reference will be stored in this Global Clips library.
- "Add Folder...": Similar to "Add File...", but it will add references to all motion clips found inside the chosen folder.
- "Remove All": Removes all references to motion data clips. The actual files are _not_ touched nor deleted, only the references are removed from the Global Clips library. The result is an empty Global Clips library.
- "Delete All": Same as "Remove All", but this time the actual motion data files are deleted, too. Rather think twice, before using this option.

#### The ... Buttons
Every Clip provides a bunch of options via a context menu presented by this button:
- "Create Scene": Inserts all characters (and props) needed by the data stored in this clip.
- "Edit...": Opens a dialog to change the name of the clip or to assign a new file to the clip.
- "Open Directory...": Opens the directory containing the motion data file in Explorer/Finder.
- "Copy to Project Clips": Copies the reference to a clip from the Global Clips library to the Project Clips library. While doing so, it also offers copy the actual motion data file into the project directory.
- "Move to Project Clips": Same as "Copy to Project Clips", but reference and file (if one opts to include it) are moved from Global Clips to Project Clips library. This means afterwards the clip can no longer be referenced from any project in Cinema 4D, but only the current one.
- "Remove": Removes the reference to the motion data clip. The actual file is _not_ touched nor deleted, only the reference is removed from the Global Clips library.
- "Delete": Same as "Remove", but this time the actual motion data file is deleted, too. Rather think twice, before using this option.


### Project Clips
This is the twin of the Global Clips. Only difference is, that clips referenced in here are only available in the current scene.


### Tags
This tab lists all Rokoko Tags existing in the current scene.
For each tag its icon (reflecting its type) and name, its parent object and object name are displayed. Three drop down menus allow to set the type of a tag, the data assigned to it as well as to choose the Actor (or Prop respectively) from those available in the assigned data. These parameters are basically reflections of the same parameters, that can be set directly on a tag in Attribute Manager.

#### The + Button
Pressing the "+" button pops up a menu to insert premade and fully configured characters (namely Rokoko Newton) or Props to the scene. All that's left to do is assign data, when "Creating Connected Studio Scene" not even this.

#### The ... Buttons
Again this button provides a contect menu per tag.
- "Play": Start the player for just this single tag
- "Go to T-Pose": Command the controlled character back to T-Pose
- "Show Tag in Attribute Manager": Exactly this, the parameters of the tag will be shown in Atttribute Manager. Similar to selecting the tag in Object Manager.
- "Show Object in Attribute Manager": The parameters of the parenting object will be shown in Atttribute Manager. Similar to selecting the object in Object Manager.
- "Delete Tag": Deletes the tag from the scene. Really only the tag, the parenting object will not be deleted.

#### Selection
On the very right hand side of the tags list there are checkboxes to select a subset of tags for the player (plus three buttons at the bottom to (de-)select all tags or invert the current selection). Using the radio buttons next to the "Start Player" button one can opt the Player to involve only those tags selected here.


#### Project Scale
All offsets in the motion data (this means the hip position for characters and position for props) are being multiplied by Project Scale during playback as well as when baking.


### Player
The Player is the main component to review motion data in a scene. This is regardless of any actual data stream actually being transmitted by Studio or just Clip data being assigned to Rokoko Tags.

#### Start/Stop Player
The moment this button gets pressed, Rokoko Studio Live will start playing any data assigned in the Rokoko Tags. Via the radio buttons right of this button, one can decide to include "All" Rokoko Tags, only those selected in the Tags tab or only those tags set to "Live" or "Clip" data. The live motion data gets buffered (indicated by the moving "Buffering" bar). One can use the buttons to pause the playback (the buffering continues in background), jump to the first or last frame. The slider allows to scrub through the buffered data for review purposes. One can even decide to start playing from the currently selected frame asyncronously to a live connection. And of course one can also resynchonize with Studio, displaying the currently incoming live data.

Pressing the button a second time ("Stop Player") flushes the data buffer and exits the Player.

#### Start Recording / Save Recording...
The moment "Start Recording" gets pressed, the live data buffer gets flushed and buffering starts from scratch. The button label changes to "Save Recording...". The functionality has already been described above.

#### Aninmate Document
Acivating this checkbox will animate all keyframed animation existing in a scene in parallel to playing back data assigned to Rokoko Tags.

#### Playback Rate
It is quite easy to setup scenes inside of Cinema 4D, which will be too complex to playback incoming live motion data. In this case the Player will drop frames. It needs to be stressed, this means really only the Player, the buffering in background is designed to keep up with Studio and should not miss frames under normal conditions. So the actual motion data recording is not affected by this and can be baked completely later on. But in such a situation, the loss of frames happens arbitrarily (meaning it's not dropping every second frame or so, but maybe a bunch of frames now and then later again another bunch of frames), resulting in a uneven looking playback. By lowering the Playback Rate with this parameter one can force the player to "willingly" drop frames (for example to only use every second or even every fourth frame) for playback, resulting in a stuttering but more even playback.


### Command API
The Command API tab offers commands to remote control Rokoko Studio.
From left to right these buttons offer the following commands:
- 'Start Recording' in Rokoko Studio
- 'Stop Recording' in Rokoko Studio
- 'Start Calibration' of all Smartsuits connected to Rokoko Studio
- 'Restart All Suits' connected to Rokoko Studio


### Menu
The Help menu offers a few web links, which might come in handy while using this plugin.

---

## Rokoko Tag in Detail

  <img src="https://user-images.githubusercontent.com/73877880/98611719-c657b980-22f2-11eb-925b-fb382a37aec0.png"/>

When created (or reassigned) the tag will automatically determine its type and depending on detected type perform automatic detection of mapping tables (described below).
When the tag is assigned to...
- a Joint or an arbitrary object with a Joint as _first_ child, the tag will assume to be of type Actor.
- an Object which carries a PoseMorph tag, the tag will assume to be of type Face.
- any other object, it will assume to be of type Prop.

Note: As also joints or objects with PoseMorph tags could be used as Props, you can always change the type of the tag to P

### Tag Properties, the Main Tab

  <img src="https://user-images.githubusercontent.com/73877880/98611801-facb7580-22f2-11eb-98da-5ba0733e2033.png"/>

- "Type": The type of the tag. It is automatically detected, when a tag is assigned. But it can be changed manually, because one may to decide to have a joint (which would lead the detection to select type Actor) behave as a Prop.
- "Stream/Clips": Offers all data sources available for a tag of the set type. This means Live data, if Rokoko Studio Live is connected, all Clips from the Global Clip library and all Clips from the Project Clip library.
- "Actors"/"Faces"/"Props": Assign an actor, face or prop from those available in the selected "Stream/Clip". One can decide to reference the actor, face or prop either by index or by name. This has consequences, when the Stream/Clip gets changed (or in case of a Live connection, the content of the transmitted stream changes). An example: Assume one of the demo scenes loaded in Studio and being streamed to Cinema 4D. The scene contains three Actors: #0 - "Mr. Orange", #1 - "Mr. White" and #2 - "Mr. Pink". If the tag now is set to "Mr. Pink (#2)" and a different scene gets loaded in Studio, only containing one actor, who is also named "Mr. Pink", the tag will atumatically use this actor. If on the other hand "Mr. Pink" was referenced by its index #2, then the tag would show "Not available", when the new scene gets loaded.

#### First Frame / Last Frame
These sliders offer means to further tweak the beginning and the end of a clip after it has been saved. These settings will be used by the Player as well as the Baking process. For example by setting the First Frame to ten, everything behaves as if the first ten frames had not been recorded.

### Control Tab

  <img src="https://user-images.githubusercontent.com/73877880/98611777-e6877880-22f2-11eb-9cc4-e7bf5baee2f5.png"/>

- "Play": Starts the Player just for this tag.
- "Go to T-Pose": (only available for tags with type Actor) Commands the contrlled character rig back to T-Pose (the one stored by "Set as T-Pose").
- "Bake Keyframes...": If a Clip is selected as data source, its data can be baked into keyframes. It's the same dialog and functionality as described above as the "Save Recording Dialog" (only without the saving options, the clip is already saved).
- "Open Rokoko Studio Live": Opens the Rokoko Studio Live Manager dialog.

### Mapping Tab
This tab is available only for tags of type Actor or Face.

#### Mapping Tab Actor

  <img src="https://user-images.githubusercontent.com/73877880/98611844-16368080-22f3-11eb-8108-d33b45c7f35b.png"/>

**Note:** It's a good idea (though not absolutely mandatory) to have the character in its T-Pose, when using the buttons and options on this tab.

"Auto Detect Rig": This already happens automatically, when the tag is assigned to an object. This button is only needed, if the rig was changed after the tag has been assigned. In order to fill the table below, the tag will try to map the joints of a rig to their body parts based on some naming conventions. Afterwards the detection result should be reviewed in the table below. In case of body parts not being found at all or body parts being assigned to wrong joints, this can be easily fixed afterwards by dragging the correct joints from Object Manager into the table.
"Set as T-Pose": Stores the current position of a character as its T-Pose. This happens automatically after rig detection, when a tag is assigned to a character rig. Additionally this happens automatically, when changing the body part/joint mapping in any way. So it shouldn't be needed that frequently. Nevertheless, if one changes the T-Pose of a character (or even forgot to have the character in T-Pose in the beginning), then one needs store the T-Pose manually using this button.
"Hip Height": Part of the rig detection is to determine the hip height of the character rig. This can be adjusted manually, for example to compensate a character floating a few centimeters above the ground due to a maybe "slighly off" T-Pose.

#### Mapping Tab Face

  <img src="https://user-images.githubusercontent.com/73877880/98611871-2189ac00-22f3-11eb-99e9-7c170ff58086.png"/>

This is basically the same as the Mapping Tab for actors. Only, it doesn't map joints to body parts, but facial morphs to Cinema 4D's PoseMorphs. Unfortunately the poses of a PoseMorph tag can not be dragged into the mapping table to correct any detect errors, but the Pose Morph names need to be entered manually.

### Mapping Presets
Both Actors and Faces can store a given Mapping setup (for an Actor the names of the joint objects, for a Face the names of the PoseMorphs). When pressing the button "Save Preset..." one gets asked for a name for the preset and that's it. Via the "Presets..." button, a preset can be apllied, renamed or deleted. So if you spent the effort of correcting a complete mapping table (maybe because the rig objects are not named in English and therefore auto detection failed completely), it's maybe a good idea to save the result as a preset for later use.


### Info Tab

  <img src="https://user-images.githubusercontent.com/73877880/98611895-2fd7c800-22f3-11eb-89db-d74e94fc2273.png"/>

The Info tab just displays some meta data about the configured actor, prop or face. Most interesting probably its name and color. This information can be faciliated for example by use of Xpresso in order to create automatic labels for characters or to influence material parameters with the color.

---

## Retargeting
Instead of directly driving a custom character with a Rokoko Tag as described above, one can also retarget motion using the new Character Definition and Solver tags new in Cinema 4D R23.

- Simply create a Newton character (or an entire Studio scene) via the "+" button in the upper left of the Tags tab in Rokoko Manager. You will find, that these characters already come with a preconfigured Character Definition tag.

- Now set up your a custom character and create a Character Definition tag as described in [Cinema 4D's documentation](https://help.maxon.net/r23/en-us/#html/TCHARACTERDEF.html).

- Finally also create a [Character Solver tag](https://help.maxon.net/r23/en-us/#html/TCHARACTERSOLVER.html%3FTocPath%3DCharacter%2520Menu%7CMotion%2520Retargeting%7CMotion%2520Solver%2520Tag%7C_____0) and drag in the two Character Definition tags (the one from Newton as Source and tthe one just created as Target)

- Done!


---

## Preferences
In Cinema 4D's preferences there's also a page for Rokoko Studio Live. Currently it provides only one single option, a checkbox to enable or disable the entire plugin. Changing this option requires a restart of Cinema 4D for the change to take effect. This checkbox is really meant as a service to our users. Should you ever run into problems with Cinema 4D (e.g. crashes,...), we'd like you to be able to exclude our plugin from the equation as easily as possible. Not because we are afraid, Rokoko Studio Live plugin could be the cause of issues, but rather to provide an easy way to prove our plugin is not the cause.



## Changelog

#### 1.0.20201109
- First version of Rokoko Studio Live for Cinema 4D
- Supported motion data: SmartsuitPro, SmartGloves, Face and Props
- Character animation and recording
- Face animation and recording
- Studio Command API support
