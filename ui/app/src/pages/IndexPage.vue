<script setup>
import { ref, onMounted } from "vue";
import { api } from "boot/axios";

const manual = ref();

onMounted(async () => {
  try {
    const resp = await api.get("/");
    manual.value = resp.data;
  } catch (err) {
    console.error(err);
  }
});

const save = () => {
  try {
    api.post("/", manual.value);
  } catch (err) {
    console.error(err);
  }
};
</script>

<template>
  <q-page class="flex flex-center">
    <div v-if="manual" class="container full-width" style="text-align: center">
    <div class="row">
      <div class="col-12">
        <q-img src="/tempweek.png" width="80%" />
      </div>
    </div>
    <div class="row">
      <div class="col-12">
        <h5>Boiler DG Elektroladung</h5>
        <q-btn-toggle
          name="genre"
          v-model="manual.dg.electro.modus"
          push
          glossy
          toggle-color="teal"
          :options="[
            { label: 'Aus', value: 'aus' },
            { label: 'Teil', value: 'teil' },
            { label: 'Voll', value: 'voll' },
          ]"
          @click="save"
        />
      </div>
    </div>
    <div class="row">
      <div class="col-12">
        <h5>Boiler UG Elektroladung</h5>
        <q-btn-toggle
          name="genre"
          v-model="manual.ug.electro.modus"
          push
          glossy
          toggle-color="teal"
          :options="[
            { label: 'Aus', value: 'aus' },
            { label: 'Teil', value: 'teil' },
            { label: 'Voll', value: 'voll' },
          ]"
          @click="save"
        />
      </div>
    </div>
    <div class="row q-mt-lg">
      <div class="col-12 q-mt-lg">
        <q-btn-toggle
          name="genre"
          v-model="manual.aux.enabled"
          push
          glossy
	  color="white"
          text-color="black"
          toggle-color="red"
          toggle-text-color="black"
          :options="[
            { label: 'AUX ein', value: true },
            { label: 'AUX aus', value: false },
          ]"
          @click="save"
        />
      </div>
    </div>
    </div>
  </q-page>
</template>
