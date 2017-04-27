


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

  //------------
  // http://stackoverflow.com/questions/20753756/how-to-change-the-html5-audio-volume-or-track-position-with-a-slider
  $(function() {

  var $aud = $("#audio_player"),
      $pp  = $('#playpause'),
      $vol = $('#volume'),
      $bar = $("#progressbar"),
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
    $pp.text(m);
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

  $pp.click(function() {
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

    updatePlaylist();

});

  function togglePlayButton(x) {
    x.classList.toggle("change");
  }