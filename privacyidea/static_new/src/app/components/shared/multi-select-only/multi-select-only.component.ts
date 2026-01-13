import { Component, input, output, computed } from "@angular/core";
import { CommonModule } from "@angular/common";
import { MatFormFieldModule } from "@angular/material/form-field";
import { MatSelectModule, MatSelectChange } from "@angular/material/select";
import { MatButtonModule } from "@angular/material/button";
import { MatTooltipModule } from "@angular/material/tooltip";

@Component({
  selector: "app-multi-select-only",
  standalone: true,
  imports: [CommonModule, MatFormFieldModule, MatSelectModule, MatButtonModule, MatTooltipModule],
  templateUrl: "./multi-select-only.component.html",
  styleUrls: ["./multi-select-only.component.scss"]
})
export class MultiSelectOnlyComponent {
  label = input<string>("");
  items = input<string[] | Set<string>>([]);
  selectedItems = input<string[]>([]);
  tooltipText = input<string>("");

  selectionChange = output<string[]>();

  uniqueItems = computed(() => [...new Set(this.items())]);
  isDisabled = computed(() => this.uniqueItems().length === 0);

  onSelectionChange(event: MatSelectChange): void {
    this.selectionChange.emit(event.value);
  }

  selectOnly(event: MouseEvent, item: string): void {
    event.stopPropagation();
    this.selectionChange.emit([item]);
  }

  isAllSelected = computed(() => {
    const items = this.uniqueItems();
    return items.length > 0 && this.selectedItems().length === items.length;
  });

  toggleAll(): void {
    this.selectionChange.emit(this.isAllSelected() ? [] : this.uniqueItems());
  }
}
