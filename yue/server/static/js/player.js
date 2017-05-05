


/*
  $(function() {
    $('a#calculate').bind('click', function() {
      $.getJSON('/_add_numbers', {
        a: $('input[name="a"]').val(),
        b: $('input[name="b"]').val()
      }, function(data) {
        $("#result").text(data.result);
      });
      return false;
    });
  });
  */

  $(function() {
    $('#btn_media_prev').click(function() {
      $.getJSON('/_media_prev', {},
        function(data) {
          //alert(data.src)
          console.log(data);
          console.log(data.path);
          //$("#audio_player").src=data.src
          var aud = $('#audio_player').get(0);
          aud.src=data.path
          aud.play()

          $("#info_artist").text(data.artist)
          $("#info_album").text(data.album)
          $("#info_title").text(data.title)
          //$("#info_index").text(data.playlist_index + "/" + data.playlist_length)

          updatePlaylist();
        });
      return false;
    });
  });

  function mediaNext() {
    $.getJSON('/_media_next', {},
      function(data) {
        //alert(data.src)
        console.log(data);
        //$("#audio_player").src=data.src
        var aud = $('#audio_player').get(0);
        aud.src=data.path
        aud.play()
        $("#info_artist").text(data.artist)
        $("#info_album").text(data.album)
        $("#info_title").text(data.title)
        //$("#info_index").text(data.playlist_index + "/" + data.playlist_length)

        updatePlaylist();
      });
    return false;
  }

  $(function() {
    $('#btn_media_next').click(mediaNext);
  });

  function mediaEnded() {
    mediaNext();
  }

  function mediaPlay() {
    $("#btn_playpause")[0].classList.remove("change");
  }

  function mediaPause() {
    $("#btn_playpause")[0].classList.add("change");
  }

  function openTab(evt, tabName) {
    // Declare all variables
    var i, tabcontent, tablinks;

    // Get all elements with class="tabcontent" and hide them
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }

    // Get all elements with class="tablinks" and remove the class "active"
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }

    // Show the current tab, and add an "active" class to the button that opened the tab
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
  }

  function updatePlaylist() {
    //return pre-formatted html for displaying the playlist
    $.ajax({
      url:'/_media_current_playlist',
      type:"get",
      dataType: "html",
      success: function(data) {
        console.log(data)
        $('#playlist_data').html(data);
      }
    });
    return false;
  }

  function pl_dragAndDrop(drag,drop) {
    //return pre-formatted html for displaying the playlist
    $.ajax({
      url:'/_media_current_playlist',
      type:"get",
      data: { "drag":drag, "drop":drop},
      dataType: "html",
      success: function(data) {
        console.log(data)
        $('#playlist_data').html(data);
      }
    });
    return false;
  }

  function pl_delete(index) {
    //return pre-formatted html for displaying the playlist
    $.ajax({
      url:'/_media_current_playlist',
      type:"get",
      data: { "delete":index},
      dataType: "html",
      success: function(data) {
        console.log(data)
        $('#playlist_data').html(data);
      }
    });
    return false;
  }

  function pl_play_index(index) {
    //return pre-formatted html for displaying the playlist
    $.getJSON('/_media_index', {"index":index},
      function(data) {
        //alert(data.src)
        console.log(data);
        //$("#audio_player").src=data.src
        var aud = $('#audio_player').get(0);
        aud.src=data.path
        aud.play()
        $("#info_artist").text(data.artist)
        $("#info_album").text(data.album)
        $("#info_title").text(data.title)
        //$("#info_index").text(data.playlist_index + "/" + data.playlist_length)

        updatePlaylist();
      });
    return false;
  }


  //------------
  // http://stackoverflow.com/questions/20753756/how-to-change-the-html5-audio-volume-or-track-position-with-a-slider
  $(function() {

  var $aud = $("#audio_player"),
      $ti  = $('#timeinfo'),
      $vol = $('#volume'),
      $bar = $("#progressbar"),
      $pp2 = $("#btn_playpause"),
      AUDIO= $aud[0];

  AUDIO.volume = 0.75;
  AUDIO.addEventListener("timeupdate", progress, false);

  function getTime(t) {
    var m=~~(t/60), s=~~(t % 60);
    return (m<10?"0"+m:m)+':'+(s<10?"0"+s:s);
  }

  function progress() {
    $bar.slider('value', ~~(100/AUDIO.duration*AUDIO.currentTime));
    var s = AUDIO.duration - AUDIO.currentTime
    var m = getTime(AUDIO.currentTime) + "/" + getTime(AUDIO.duration)
    m = m + " - " + getTime(s)
    $ti.text(m);
  }

  $vol.slider( {
    value : AUDIO.volume*100,
    slide : function(ev, ui) {
      $vol.css({background:"hsla(180,"+ui.value+"%,50%,1)"});
      AUDIO.volume = ui.value/100;
    }
  });

  $bar.slider( {
    value : AUDIO.currentTime,
    slide : function(ev, ui) {
      AUDIO.currentTime = AUDIO.duration/100*ui.value;
    }
  });

  $pp2.click(function() {
    return AUDIO[AUDIO.paused?'play':'pause']();
  });

});
  //------------

$(document).ready(function(){


    //$(":button").css("background-color", "red");

    /*$("#btn1").click(function(){
        alert("on click")
        $("#audio_player").src="/media/002"
    });*/

    document.getElementById("defaultOpen").click();

    $("#btn_playpause")[0].classList.add("change");

    updatePlaylist();

    getApiKey(false);

});

  function togglePlayButton(x) {
    x.classList.toggle("change");
  }


  var idx_drag_start=-1;
  var idx_drag_hover=-1;
  function pl_allowDrop(ev) {
    var id = "" + ev.target.id;
    if (id.startsWith("plelem")) {
      idx_drag_hover=ev.target.id;
      ev.preventDefault();
    }
  }

  function pl_drag(ev) {
    idx_drag_start=ev.target.id;
    ev.dataTransfer.setData("text", ev.target.id);
  }

  function pl_drop(ev) {
    ev.preventDefault();
    var idx_drag_end = ev.target.id

    var id1 = idx_drag_start.split("_")[1]
    var id2 = (""+idx_drag_hover).split("_")[1]
    var id3 = (""+idx_drag_end).split("_")[1]

    console.log( "1:" + id1 + "> 2:" + id2+"> 3:" + id3+">");
    if (id2=="") {
      console.log("drop has no target");
      return false;
    }

    if (id1==id2) {
      console.log("drop target is source");
      return false;
    }

    console.log("drop success");
    pl_dragAndDrop(id1,id2);
  }



function getApiKey(regen) {
    //return pre-formatted html for displaying the playlist
    console.log("regen"+regen)
    $.ajax({
      url:'/user/api_key',
      type:"get",
      data: { "regen":regen },
      dataType: "html",
      success: function(data) {
        console.log(data)
        $('#api_key').html(data);
      }
    });
    return false;
  }

function createUser() {

    var email = $("#create_user_email").val();
    var admin = $("#create_user_admin").is(':checked');
    $.ajax({
      url:'/user/register',
      type:"get",
      data: { "email":email,"admin":admin},
      dataType: "html",
      success: function(data) {
        $('#create_user_result').html(data);
      },
      error: function(request, status, error) {
        $('#create_user_result').html(request.responseText);
      }
    });
}