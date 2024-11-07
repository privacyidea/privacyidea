import {Component, Input, WritableSignal} from '@angular/core';
import {MatIcon} from '@angular/material/icon';
import {MatTab, MatTabLabel} from '@angular/material/tabs';
import {MatList, MatListItem} from '@angular/material/list';
import {MatButton} from '@angular/material/button';
import {MatDivider} from '@angular/material/divider';
import {animate, state, style, transition, trigger} from '@angular/animations';
import {NgClass} from '@angular/common';

@Component({
  selector: 'app-token-tab',
  standalone: true,
  imports: [
    MatIcon,
    MatTab,
    MatList,
    MatListItem,
    MatTabLabel,
    MatButton,
    MatDivider,
    NgClass
  ],
  templateUrl: './token-tab.component.html',
  styleUrl: './token-tab.component.css',
  animations: [
    trigger('toggleState', [
      state('false', style({
        transform: 'translateY(0)'
      })),
      state('true', style({
        transform: 'translateY(0)'
      })),
      transition('false => true', [
        style({
          transform: 'translateY(50%)'
        }),
        animate('200ms ease-in', style({
          transform: 'translateY(0)'
        }))
      ]),
      transition('true => false', [
        style({
          transform: 'translateY(50%)'
        }),
        animate('200ms ease-out', style({
          transform: 'translateY(0)'
        }))
      ])
    ])
  ]
})
export class TokenTabComponent {
  @Input() tokenIsSelected!: WritableSignal<boolean>;
}
