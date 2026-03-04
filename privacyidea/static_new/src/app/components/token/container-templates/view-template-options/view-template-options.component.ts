import { Component, input } from "@angular/core";
import { MatCardModule } from "@angular/material/card";
import { MatListModule } from "@angular/material/list";
import { CommonModule } from "@angular/common";
import { AbstractDialogComponent } from "@components/shared/dialog/abstract-dialog/abstract-dialog.component";

@Component({
  selector: "app-view-template-options",
  standalone: true,
  imports: [CommonModule, MatCardModule, MatListModule],
  templateUrl: "./view-template-options.component.html",
  styleUrl: "./view-template-options.component.scss"
})
export class ViewTemplateOptionsComponent extends AbstractDialogComponent {
  readonly templateOptions = input.required<{
    options: any;
    tokens: Array<any>;
  }>();
}
