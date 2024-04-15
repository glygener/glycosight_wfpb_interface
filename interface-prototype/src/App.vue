<template>
  <v-app>
      <div class="text-center">
      <h2>Welcome to the GlycoSight file upload testing range</h2>
      </div>
    <v-main>
      <FileUpload upload-target-u-r-l="test" />
    </v-main>
  </v-app>
</template>

<script setup>
  import FileUpload from './components/FileUpload.vue';

</script>
