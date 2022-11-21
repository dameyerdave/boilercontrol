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
    <q-img src="/tempweek.png" width="80%" />
    <div v-if="manual" class="row">
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
  </q-page>
</template>
