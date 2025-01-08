import {Component, Input, WritableSignal} from '@angular/core';
import {MatIcon} from '@angular/material/icon';
import {MatList, MatListItem} from '@angular/material/list';
import {MatButton} from '@angular/material/button';
import {NgClass} from '@angular/common';
import {tabToggleState} from '../../../../../styles/animations/animations';
import {MatDivider} from "@angular/material/divider";
import {switchMap} from 'rxjs';
import {ContainerService} from '../../../../services/container/container.service';

@Component({
  selector: 'app-container-tab',
  standalone: true,
    imports: [
        MatIcon,
        MatList,
        MatListItem,
        MatButton,
        NgClass,
        MatDivider
    ],
  templateUrl: './container-tab.component.html',
  styleUrl: './container-tab.component.scss',
  animations: [tabToggleState]
})
export class ContainerTabComponent {
  @Input() containerIsSelected!: WritableSignal<boolean>;
  @Input() serial!: WritableSignal<string>
  @Input() states!: WritableSignal<string[]>
  @Input() refreshContainerDetails!: WritableSignal<boolean>;

  constructor(private containerService: ContainerService,) {
  }

  toggleActive(): void {
    this.containerService.toggleActive(this.serial(), this.states()).pipe(
      switchMap(() => this.containerService.getContainerDetails(this.serial()))
    ).subscribe({
      next: () => {
        this.refreshContainerDetails.set(true);
      },
      error: error => {
        console.error('Failed to toggle active', error);
      }
    });
  }
}
