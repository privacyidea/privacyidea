import { Component, computed, effect, input } from "@angular/core";
import { AddedActionsListComponent } from "../policy-panels/action-tab/added-actions-list/added-actions-list.component";

@Component({
  selector: "app-policies-view-action-row",
  standalone: true,
  templateUrl: "./policies-view-action-row.component.html",
  styleUrl: "./policies-view-action-row.component.scss",
  imports: [AddedActionsListComponent]
})
export class PoliciesViewActionRowComponent {
  readonly actions = input.required<{ [actionName: string]: any }>();
  readonly actionsList = computed(() =>
    Object.entries(this.actions()).map(([name, value]) => ({ name: name, value: value }))
  );
  constructor() {
    effect(() => {
      console.log("PoliciesViewActionRowComponent - actions:", this.actions());
    });
  }
}
